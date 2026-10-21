from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.schemas.dashboard import (
    DashboardSummaryRead,
    ModalityCountRead,
    PendingEnrollmentRead,
    RecentEnrollmentRead,
)
from dojoflow.services.billing import BillingService
from dojoflow.shared.enums import EnrollmentStatus

RECENT_ENROLLMENTS_LIMIT = 5


class DashboardService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def summary(self, academy_id: int) -> DashboardSummaryRead:
        billing = BillingService(self.db_session)
        lists = await billing.dashboard_lists(academy_id)

        return DashboardSummaryRead(
            active_students=await self._active_students(academy_id),
            students_by_modality=await self._by_modality(academy_id),
            recent_enrollments=await self._recent(academy_id),
            registration_pending=await self._pending(academy_id),
            overdue=lists.overdue,
            due_soon=lists.due_soon,
            overdue_students=lists.overdue_students,
            due_soon_students=lists.due_soon_students,
        )

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
