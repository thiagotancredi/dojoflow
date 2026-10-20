from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.graduation_list import GraduationList, GraduationListEntry
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.graduation_list import GraduationListRepository
from dojoflow.repositories.graduation_list_entry import (
    GraduationListEntryRepository,
)
from dojoflow.schemas.graduation_list import (
    GraduationCandidate,
    GraduationListCreate,
    GraduationListDetail,
    GraduationListSummary,
    GraduationListUpdate,
)
from dojoflow.services.belt import BeltService, next_in_sequence
from dojoflow.services.belt_rules import evaluate_eligibility
from dojoflow.services.enrollment_belt import EnrollmentBeltService
from dojoflow.shared.enums import EnrollmentStatus
from dojoflow.shared.exceptions import ConflictError, NotFoundError


def _summaries_query(academy_id: int) -> Select[Any]:
    entry_count = (
        select(func.count(GraduationListEntry.id))
        .where(GraduationListEntry.graduation_list_id == GraduationList.id)
        .scalar_subquery()
    )

    return (
        select(
            GraduationList.id,
            GraduationList.public_id,
            GraduationList.name,
            GraduationList.modality_id,
            Modality.public_id.label('modality_public_id'),
            Modality.name.label('modality_name'),
            Modality.emoji.label('modality_emoji'),
            GraduationList.exam_date,
            GraduationList.created_at,
            entry_count.label('entry_count'),
        )
        .join(Modality, Modality.id == GraduationList.modality_id)
        .where(GraduationList.academy_id == academy_id)
    )


class GraduationListService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        graduation_list_repository: GraduationListRepository,
        graduation_list_entry_repository: GraduationListEntryRepository,
        belt_service: BeltService,
        enrollment_belt_service: EnrollmentBeltService,
        academy_modality_repository: AcademyModalityRepository,
        db_session: AsyncSession,
    ) -> None:
        self.graduation_list_repository = graduation_list_repository
        self.graduation_list_entry_repository = (
            graduation_list_entry_repository
        )
        self.belt_service = belt_service
        self.enrollment_belt_service = enrollment_belt_service
        self.academy_modality_repository = academy_modality_repository
        self.db_session = db_session

    async def list_summaries(
        self,
        academy_id: int,
    ) -> list[GraduationListSummary]:
        stmt = _summaries_query(academy_id).order_by(
            GraduationList.exam_date.desc(), GraduationList.id.desc()
        )
        result = await self.db_session.execute(stmt)

        return [
            GraduationListSummary(**row) for row in result.mappings().all()
        ]

    async def get_summary(
        self,
        academy_id: int,
        list_id: int,
    ) -> GraduationListSummary:
        stmt = _summaries_query(academy_id).where(GraduationList.id == list_id)
        row = (await self.db_session.execute(stmt)).mappings().one_or_none()

        if row is None:
            raise NotFoundError(
                'Could not find this graduation list.',
                code='GRADUATION_LIST_NOT_FOUND',
            )

        return GraduationListSummary(**row)

    @transactional
    async def create(
        self,
        academy_id: int,
        data: GraduationListCreate,
    ) -> GraduationListSummary:
        enabled = await self.academy_modality_repository.exists(
            filters=[
                AcademyModality.academy_id == academy_id,
                AcademyModality.modality_id == data.modality_id,
            ],
        )

        if not enabled:
            raise NotFoundError(
                'This modality is not configured for this academy.',
                code='MODALITY_NOT_ENABLED',
            )

        if not await self.belt_service.list_by_modality(
            academy_id, data.modality_id
        ):
            raise ConflictError(
                'This modality has no belts yet.',
                code='MODALITY_HAS_NO_BELTS',
            )

        list_id = await self.graduation_list_repository.create({
            **data.model_dump(),
            'academy_id': academy_id,
        })

        return await self.get_summary(academy_id, list_id)

    async def get_detail(
        self,
        academy_id: int,
        list_id: int,
    ) -> GraduationListDetail:
        summary = await self.get_summary(academy_id, list_id)
        belts = await self.belt_service.list_by_modality(
            academy_id, summary.modality_id
        )

        return GraduationListDetail(
            summary=summary,
            belts=belts,
            entries=[],
            candidates=await self._candidates(academy_id, summary, belts),
        )

    @transactional
    async def update(
        self,
        academy_id: int,
        list_id: int,
        data: GraduationListUpdate,
    ) -> None:
        await self.get_summary(academy_id, list_id)
        payload = data.model_dump(exclude_unset=True)

        if payload:
            await self.graduation_list_repository.update_by_id(
                list_id, payload
            )

    @transactional
    async def delete(self, academy_id: int, list_id: int) -> None:
        await self.get_summary(academy_id, list_id)

        await self.db_session.execute(
            delete(GraduationListEntry).where(
                GraduationListEntry.graduation_list_id == list_id
            )
        )
        await self.graduation_list_repository.delete_by_id(list_id)

    async def _candidates(
        self,
        academy_id: int,
        summary: GraduationListSummary,
        belts: list[Any],
    ) -> list[GraduationCandidate]:
        already_in_list = select(GraduationListEntry.enrollment_id).where(
            GraduationListEntry.graduation_list_id == summary.id
        )
        stmt = (
            select(
                Enrollment.id,
                Enrollment.public_id,
                Student.name,
            )
            .join(Student, Student.id == Enrollment.student_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.modality_id == summary.modality_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Enrollment.id.not_in(already_in_list),
            )
            .order_by(Student.name, Enrollment.id)
        )
        rows = (await self.db_session.execute(stmt)).mappings().all()
        current_belts = await self.enrollment_belt_service.current_belts(
            academy_id, [row['id'] for row in rows]
        )

        candidates = []

        for row in rows:
            current = current_belts.get(row['id'])
            candidates.append(
                GraduationCandidate(
                    enrollment_id=row['id'],
                    enrollment_public_id=row['public_id'],
                    student_name=row['name'],
                    current=current,
                    eligibility=evaluate_eligibility(
                        current.graduated_on if current else None,
                        current.belt.min_time_amount if current else None,
                        current.belt.min_time_unit if current else None,
                        summary.exam_date,
                    ),
                    suggested_target=next_in_sequence(
                        belts, current.belt.id if current else None
                    ),
                )
            )

        return candidates
