from calendar import isleap
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.belt import Belt
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.schemas.dashboard import (
    AgeGroup,
    AgeGroupCountRead,
    AgeGroupsRead,
    BeltCountRead,
    BirthdayRead,
    DashboardSummaryRead,
    ModalityAgeGroupsRead,
    ModalityBeltsRead,
    ModalityCountRead,
    MonthCountRead,
    SexCountRead,
)
from dojoflow.services.belt_rules import ACADEMY_TIMEZONE, local_today
from dojoflow.shared.enums import EnrollmentStatus, StudentSex

NEW_STUDENTS_MONTHS = 12
SEX_ORDER: tuple[StudentSex | None, ...] = (
    StudentSex.FEMALE,
    StudentSex.MALE,
    StudentSex.OTHER,
    None,
)
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
        today = local_today()
        active = await self._active_rows(academy_id)

        return DashboardSummaryRead(
            active_students=await self._active_students(academy_id),
            students_by_modality=await self._by_modality(academy_id),
            age_groups=self._age_groups(active, today),
            birthdays=self._birthdays(active, today),
            new_students_by_month=await self._new_students(academy_id, today),
            by_belt=await self._by_belt(academy_id),
            by_sex=self._by_sex(active),
        )

    async def _active_rows(self, academy_id: int) -> list[dict[str, Any]]:
        """Uma linha por matrícula ativa: aluno, nascimento e modalidade."""
        stmt = (
            select(
                Student.id.label('student_id'),
                Student.public_id.label('student_public_id'),
                Student.name,
                Student.birth_date,
                Student.sex,
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

    @staticmethod
    def _by_sex(rows: list[dict[str, Any]]) -> list[SexCountRead]:
        students = {row['student_id']: row['sex'] for row in rows}
        counts = dict.fromkeys(SEX_ORDER, 0)
        for sex in students.values():
            counts[sex] += 1
        return [
            SexCountRead(sex=sex, count=count)
            for sex, count in counts.items()
            if count > 0
        ]

    async def _by_belt(self, academy_id: int) -> list[ModalityBeltsRead]:
        """Matrículas ativas pela faixa atual (o registro mais recente)."""
        current = (
            select(EnrollmentBelt.enrollment_id, EnrollmentBelt.belt_id)
            .where(EnrollmentBelt.academy_id == academy_id)
            .distinct(EnrollmentBelt.enrollment_id)
            .order_by(
                EnrollmentBelt.enrollment_id,
                EnrollmentBelt.graduated_on.desc(),
                EnrollmentBelt.id.desc(),
            )
            .subquery()
        )
        rows = (
            await self.db_session.execute(
                select(Enrollment.modality_id, current.c.belt_id)
                .outerjoin(current, current.c.enrollment_id == Enrollment.id)
                .where(
                    Enrollment.academy_id == academy_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
        ).all()
        if not rows:
            return []

        counts: dict[int | None, int] = {}
        without: dict[int, int] = {}
        for modality_id, belt_id in rows:
            if belt_id is None:
                without[modality_id] = without.get(modality_id, 0) + 1
            else:
                counts[belt_id] = counts.get(belt_id, 0) + 1

        modality_ids = {modality_id for modality_id, _ in rows}
        modalities = (
            await self.db_session.execute(
                select(Modality.id, Modality.public_id, Modality.name)
                .where(Modality.id.in_(modality_ids))
                .order_by(Modality.name)
            )
        ).all()
        belts = (
            await self.db_session.scalars(
                select(Belt)
                .where(
                    Belt.academy_id == academy_id,
                    Belt.modality_id.in_(modality_ids),
                )
                .order_by(Belt.position, Belt.id)
            )
        ).all()

        return [
            ModalityBeltsRead(
                modality_id=public_id,
                modality_name=name,
                belts=[
                    BeltCountRead(
                        id=belt.public_id,
                        name=belt.name,
                        primary_color=belt.primary_color,
                        stripe_color=belt.stripe_color,
                        marks=belt.marks,
                        marks_color=belt.marks_color,
                        tip_color=belt.tip_color,
                        count=counts.get(belt.id, 0),
                    )
                    for belt in belts
                    if belt.modality_id == modality_id
                ],
                without_belt=without.get(modality_id, 0),
            )
            for modality_id, public_id, name in modalities
        ]
