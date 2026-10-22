from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.belt import Belt
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.modality import Modality
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.modality import ModalityRepository
from dojoflow.schemas.modality import ModalityOptionRead, ModalityRead
from dojoflow.shared.enums import EnrollmentStatus
from dojoflow.shared.exceptions import ConflictError, NotFoundError


class ModalityService:
    def __init__(
        self,
        modality_repository: ModalityRepository,
        academy_modality_repository: AcademyModalityRepository,
        db_session: AsyncSession,
    ) -> None:
        self.modality_repository = modality_repository
        self.academy_modality_repository = academy_modality_repository
        self.db_session = db_session

    async def list_catalog(self) -> list[ModalityRead]:
        modalities = await self.modality_repository.list(
            filters=[
                Modality.is_active.is_(True),
            ],
            order_by=[
                Modality.name,
            ],
        )

        return [ModalityRead(**modality) for modality in modalities]

    async def list_academy_options(
        self,
        academy_id: int,
    ) -> list[ModalityOptionRead]:
        modalities = await self.list_catalog()
        selected_modality_ids = await self.get_selected_modality_ids(
            academy_id
        )
        pending_counts = await self._count_enrollments_without_belt(academy_id)
        belt_counts = await self._count_belts(academy_id)
        active_counts = await self._count_active_enrollments(academy_id)

        return [
            ModalityOptionRead(
                id=modality.id,
                public_id=modality.public_id,
                name=modality.name,
                emoji=modality.emoji,
                is_selected=modality.id in selected_modality_ids,
                has_belts=belt_counts.get(modality.id, 0) > 0,
                belt_count=belt_counts.get(modality.id, 0),
                active_enrollment_count=active_counts.get(modality.id, 0),
                pending_belt_count=pending_counts.get(modality.id, 0),
            )
            for modality in modalities
        ]

    async def _count_active_enrollments(
        self,
        academy_id: int,
    ) -> dict[int, int]:
        stmt = (
            select(Enrollment.modality_id, func.count(Enrollment.id))
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
            .group_by(Enrollment.modality_id)
        )
        result = await self.db_session.execute(stmt)

        return dict(result.tuples().all())

    async def _count_belts(self, academy_id: int) -> dict[int, int]:
        stmt = (
            select(Belt.modality_id, func.count(Belt.id))
            .where(Belt.academy_id == academy_id)
            .group_by(Belt.modality_id)
        )
        result = await self.db_session.execute(stmt)

        return dict(result.tuples().all())

    async def _count_enrollments_without_belt(
        self,
        academy_id: int,
    ) -> dict[int, int]:
        has_belt = exists().where(
            EnrollmentBelt.enrollment_id == Enrollment.id
        )
        stmt = (
            select(Enrollment.modality_id, func.count(Enrollment.id))
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                ~has_belt,
            )
            .group_by(Enrollment.modality_id)
        )
        result = await self.db_session.execute(stmt)

        return dict(result.tuples().all())

    async def get_selected_modality_ids(
        self,
        academy_id: int,
    ) -> set[int]:
        academy_modalities = await self.academy_modality_repository.list(
            filters=[
                AcademyModality.academy_id == academy_id,
            ],
        )

        return {
            academy_modality['modality_id']
            for academy_modality in academy_modalities
        }

    @transactional
    async def toggle_academy_modality(
        self,
        academy_id: int,
        modality_id: int,
    ) -> bool:
        await self._ensure_active_modality_exists(modality_id)

        academy_modality = await self.academy_modality_repository.get_one(
            filters=[
                AcademyModality.academy_id == academy_id,
                AcademyModality.modality_id == modality_id,
            ],
        )

        if academy_modality is not None:
            # Só sai da academia quem não tem aluno com matrícula ativa
            # (vale para o site e para o bot)
            active_counts = await self._count_active_enrollments(academy_id)

            if active_counts.get(modality_id, 0) > 0:
                raise ConflictError(
                    'This modality has students with active enrollments.',
                    code='MODALITY_HAS_ACTIVE_ENROLLMENTS',
                )

            await self.academy_modality_repository.delete_by_id(
                academy_modality['id']
            )

            return False

        await self.academy_modality_repository.create({
            'academy_id': academy_id,
            'modality_id': modality_id,
        })

        return True

    async def _ensure_active_modality_exists(
        self,
        modality_id: int,
    ) -> None:
        modality = await self.modality_repository.get_one(
            filters=[
                Modality.id == modality_id,
                Modality.is_active.is_(True),
            ],
        )

        if modality is None:
            raise NotFoundError('Could not find this active modality.')
