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
from dojoflow.schemas.belt import BeltRead
from dojoflow.schemas.graduation_list import (
    GraduationCandidate,
    GraduationEntry,
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
            entries=await self._entries(summary, belts),
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

    @transactional
    async def add_entry(
        self,
        academy_id: int,
        list_id: int,
        enrollment_id: int,
        target_belt_id: int | None,
    ) -> None:
        summary = await self.get_summary(academy_id, list_id)
        enrollment = (
            (
                await self.db_session.execute(
                    select(Enrollment.modality_id, Enrollment.status).where(
                        Enrollment.id == enrollment_id,
                        Enrollment.academy_id == academy_id,
                    )
                )
            )
            .mappings()
            .one()
        )

        if (
            enrollment['modality_id'] != summary.modality_id
            or enrollment['status'] != EnrollmentStatus.ACTIVE
        ):
            raise ConflictError(
                'Only active enrollments of this modality can be added.',
                code='ENROLLMENT_NOT_CANDIDATE',
            )

        if await self.graduation_list_entry_repository.exists(
            filters=[
                GraduationListEntry.graduation_list_id == list_id,
                GraduationListEntry.enrollment_id == enrollment_id,
            ],
        ):
            raise ConflictError(
                'This student is already in the list.',
                code='ALREADY_IN_LIST',
            )

        current = (
            await self.enrollment_belt_service.current_belts(
                academy_id, [enrollment_id]
            )
        ).get(enrollment_id)
        target = await self._resolve_target(
            academy_id,
            summary,
            current.belt.id if current else None,
            target_belt_id,
        )

        await self.graduation_list_entry_repository.create({
            'academy_id': academy_id,
            'graduation_list_id': list_id,
            'enrollment_id': enrollment_id,
            'target_belt_id': target.id,
            'snapshot_belt_id': current.belt.id if current else None,
            'snapshot_graduated_on': current.graduated_on if current else None,
        })

    @transactional
    async def update_entry(
        self,
        academy_id: int,
        list_id: int,
        entry_id: int,
        target_belt_id: int,
    ) -> None:
        summary = await self.get_summary(academy_id, list_id)
        target = await self._resolve_target(
            academy_id, summary, None, target_belt_id
        )

        await self.graduation_list_entry_repository.update_by_id(
            entry_id, {'target_belt_id': target.id}
        )

    @transactional
    async def remove_entry(
        self,
        academy_id: int,
        list_id: int,
        entry_id: int,
    ) -> None:
        await self.get_summary(academy_id, list_id)
        await self.graduation_list_entry_repository.delete_by_id(entry_id)

    async def _resolve_target(
        self,
        academy_id: int,
        summary: GraduationListSummary,
        current_belt_id: int | None,
        target_belt_id: int | None,
    ) -> BeltRead:
        if target_belt_id is None:
            belts = await self.belt_service.list_by_modality(
                academy_id, summary.modality_id
            )
            target = next_in_sequence(belts, current_belt_id)

            if target is None:
                raise ConflictError(
                    'This student is already in the last belt; '
                    'choose the target belt.',
                    code='TARGET_BELT_REQUIRED',
                )

            return target

        target = await self.belt_service.get(academy_id, target_belt_id)

        if target.modality_id != summary.modality_id:
            raise ConflictError(
                'This belt belongs to another modality.',
                code='BELT_MODALITY_MISMATCH',
            )

        return target

    async def _entries(
        self,
        summary: GraduationListSummary,
        belts: list[BeltRead],
    ) -> list[GraduationEntry]:
        stmt = (
            select(
                GraduationListEntry.id,
                GraduationListEntry.public_id,
                GraduationListEntry.enrollment_id,
                GraduationListEntry.target_belt_id,
                GraduationListEntry.snapshot_belt_id,
                GraduationListEntry.snapshot_graduated_on,
                Enrollment.public_id.label('enrollment_public_id'),
                Student.name.label('student_name'),
            )
            .join(
                Enrollment, Enrollment.id == GraduationListEntry.enrollment_id
            )
            .join(Student, Student.id == Enrollment.student_id)
            .where(GraduationListEntry.graduation_list_id == summary.id)
            .order_by(Student.name, GraduationListEntry.id)
        )
        rows = (await self.db_session.execute(stmt)).mappings().all()
        # Faixas do retrato e pretendida são sempre da modalidade da lista
        belts_by_id = {belt.id: belt for belt in belts}

        entries = []

        for row in rows:
            snapshot = belts_by_id.get(row['snapshot_belt_id'])
            entries.append(
                GraduationEntry(
                    id=row['id'],
                    public_id=row['public_id'],
                    enrollment_id=row['enrollment_id'],
                    enrollment_public_id=row['enrollment_public_id'],
                    student_name=row['student_name'],
                    snapshot_belt=snapshot,
                    snapshot_graduated_on=row['snapshot_graduated_on'],
                    eligibility=evaluate_eligibility(
                        row['snapshot_graduated_on'],
                        snapshot.min_time_amount if snapshot else None,
                        snapshot.min_time_unit if snapshot else None,
                        summary.exam_date,
                    ),
                    target_belt=belts_by_id[row['target_belt_id']],
                )
            )

        return entries

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
