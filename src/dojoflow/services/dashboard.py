from calendar import isleap
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.schemas.dashboard import (
    AgeGroup,
    AgeGroupCountRead,
    AgeGroupsRead,
    BirthdayRead,
    DashboardSummaryRead,
    ModalityAgeGroupsRead,
    ModalityCountRead,
    MonthCountRead,
    PendingEnrollmentRead,
    RecentEnrollmentRead,
)
from dojoflow.services.belt_rules import ACADEMY_TIMEZONE, local_today
from dojoflow.services.billing import BillingService
from dojoflow.shared.enums import EnrollmentStatus

RECENT_ENROLLMENTS_LIMIT = 5
NEW_STUDENTS_MONTHS = 6
AGE_GROUPS: tuple[AgeGroup, ...] = (
    'kids',
    'juvenile',
    'adult',
    'master',
    'unknown',
)
KIDS_MAX_AGE = 12
JUVENILE_MAX_AGE = 17
ADULT_MAX_AGE = 39
FEBRUARY = 2
LEAP_DAY = 29


def completed_years(birth: date, today: date) -> int:
    before_birthday = (today.month, today.day) < (birth.month, birth.day)
    return today.year - birth.year - int(before_birthday)


def age_group(birth: date | None, today: date) -> AgeGroup:
    if birth is None:
        return 'unknown'

    age = completed_years(birth, today)

    if age <= KIDS_MAX_AGE:
        return 'kids'
    if age <= JUVENILE_MAX_AGE:
        return 'juvenile'
    if age <= ADULT_MAX_AGE:
        return 'adult'
    return 'master'


def birthday_day_in(birth: date, year: int) -> int:
    # 29/02 vira 28/02 nos anos que não são bissextos
    if birth.month == FEBRUARY and birth.day == LEAP_DAY and not isleap(year):
        return LEAP_DAY - 1
    return birth.day


def add_months(month: date, delta: int) -> date:
    index = month.year * 12 + month.month - 1 + delta
    return date(index // 12, index % 12 + 1, 1)


def _count_groups(
    births: list[date | None], today: date
) -> list[AgeGroupCountRead]:
    counts = dict.fromkeys(AGE_GROUPS, 0)
    for birth in births:
        counts[age_group(birth, today)] += 1
    return [AgeGroupCountRead(group=g, count=counts[g]) for g in AGE_GROUPS]


class DashboardService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def summary(self, academy_id: int) -> DashboardSummaryRead:
        billing = BillingService(self.db_session)
        lists = await billing.dashboard_lists(academy_id)

        today = local_today()
        active = await self._active_rows(academy_id)

        return DashboardSummaryRead(
            active_students=await self._active_students(academy_id),
            students_by_modality=await self._by_modality(academy_id),
            recent_enrollments=await self._recent(academy_id),
            registration_pending=await self._pending(academy_id),
            overdue=lists.overdue,
            due_soon=lists.due_soon,
            overdue_students=lists.overdue_students,
            due_soon_students=lists.due_soon_students,
            overdue_total=lists.overdue_total,
            age_groups=self._age_groups(active, today),
            birthdays=self._birthdays(active, today),
            new_students_by_month=await self._new_students(academy_id, today),
        )

    async def _active_rows(self, academy_id: int) -> list[dict[str, Any]]:
        """Uma linha por matrícula ativa: aluno, nascimento e modalidade."""
        stmt = (
            select(
                Student.id.label('student_id'),
                Student.public_id.label('student_public_id'),
                Student.name,
                Student.birth_date,
                Modality.public_id.label('modality_id'),
                Modality.name.label('modality_name'),
            )
            .select_from(Enrollment)
            .join(Student, Student.id == Enrollment.student_id)
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        result = await self.db_session.execute(stmt)

        return [dict(row) for row in result.mappings()]

    @staticmethod
    def _age_groups(rows: list[dict[str, Any]], today: date) -> AgeGroupsRead:
        students = {row['student_id']: row['birth_date'] for row in rows}
        modalities: dict[Any, tuple[str, dict[int, date | None]]] = {}

        for row in rows:
            _, births = modalities.setdefault(
                row['modality_id'], (row['modality_name'], {})
            )
            births[row['student_id']] = row['birth_date']

        return AgeGroupsRead(
            all=_count_groups(list(students.values()), today),
            by_modality=[
                ModalityAgeGroupsRead(
                    modality_id=modality_id,
                    modality_name=name,
                    groups=_count_groups(list(births.values()), today),
                )
                for modality_id, (name, births) in sorted(
                    modalities.items(), key=lambda item: item[1][0]
                )
            ],
        )

    @staticmethod
    def _birthdays(
        rows: list[dict[str, Any]], today: date
    ) -> list[BirthdayRead]:
        students = {row['student_id']: row for row in rows}
        birthdays = []

        for row in students.values():
            birth = row['birth_date']
            if birth is None or birth.month != today.month:
                continue
            day = birthday_day_in(birth, today.year)
            birthdays.append(
                BirthdayRead(
                    student_id=row['student_public_id'],
                    name=row['name'],
                    day=day,
                    turning_age=today.year - birth.year,
                    is_today=day == today.day,
                )
            )

        return sorted(birthdays, key=lambda b: (b.day, b.name))

    async def _new_students(
        self,
        academy_id: int,
        today: date,
    ) -> list[MonthCountRead]:
        """Alunos pelo mês da primeira matrícula (fuso da academia)."""
        current = today.replace(day=1)
        first_month = add_months(current, -(NEW_STUDENTS_MONTHS - 1))
        since = datetime.combine(first_month, time.min, ACADEMY_TIMEZONE)
        first_enrollment = func.min(Enrollment.created_at)
        stmt = (
            select(first_enrollment)
            .where(Enrollment.academy_id == academy_id)
            .group_by(Enrollment.student_id)
            .having(first_enrollment >= since)
        )
        counts: dict[date, int] = {}

        for created_at in (await self.db_session.scalars(stmt)).all():
            month = (
                created_at.astimezone(ACADEMY_TIMEZONE).date().replace(day=1)
            )
            counts[month] = counts.get(month, 0) + 1

        return [
            MonthCountRead(month=month, count=counts.get(month, 0))
            for month in (
                add_months(first_month, offset)
                for offset in range(NEW_STUDENTS_MONTHS)
            )
        ]

    async def _active_students(self, academy_id: int) -> int:
        total = await self.db_session.scalar(
            select(func.count(distinct(Enrollment.student_id))).where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )

        return int(total or 0)

    async def _by_modality(self, academy_id: int) -> list[ModalityCountRead]:
        count = func.count(distinct(Enrollment.student_id)).label('count')
        stmt = (
            select(
                Modality.public_id.label('modality_id'),
                Modality.name.label('modality_name'),
                count,
            )
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
            .group_by(Modality.public_id, Modality.name)
            .order_by(count.desc(), Modality.name)
        )
        result = await self.db_session.execute(stmt)

        return [ModalityCountRead(**row) for row in result.mappings()]

    async def _recent(self, academy_id: int) -> list[RecentEnrollmentRead]:
        stmt = (
            select(
                Student.public_id.label('student_id'),
                Student.name.label('student_name'),
                Modality.name.label('modality_name'),
                Enrollment.created_at,
            )
            .join(Student, Student.id == Enrollment.student_id)
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(Enrollment.academy_id == academy_id)
            .order_by(Enrollment.created_at.desc(), Enrollment.id.desc())
            .limit(RECENT_ENROLLMENTS_LIMIT)
        )
        result = await self.db_session.execute(stmt)

        return [RecentEnrollmentRead(**row) for row in result.mappings()]

    async def _pending(self, academy_id: int) -> list[PendingEnrollmentRead]:
        stmt = (
            select(
                Enrollment.public_id.label('enrollment_id'),
                Student.public_id.label('student_id'),
                Student.name.label('student_name'),
                Modality.name.label('modality_name'),
            )
            .join(Student, Student.id == Enrollment.student_id)
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Enrollment.is_exempt.is_(False),
                or_(
                    Enrollment.monthly_fee.is_(None),
                    Enrollment.due_day.is_(None),
                ),
            )
            .order_by(Student.name, Modality.name)
        )
        result = await self.db_session.execute(stmt)

        return [PendingEnrollmentRead(**row) for row in result.mappings()]
