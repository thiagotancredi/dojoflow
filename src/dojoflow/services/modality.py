from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.modality import Modality
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.modality import ModalityRepository
from dojoflow.schemas.modality import ModalityOptionRead, ModalityRead
from dojoflow.shared.exceptions import NotFoundError


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

    async def list_selected_by_academy(
        self,
        academy_id: int,
    ) -> list[ModalityRead]:
        stmt = (
            select(
                Modality.id,
                Modality.name,
                Modality.emoji,
                Modality.is_active,
            )
            .join(
                AcademyModality,
                AcademyModality.modality_id == Modality.id,
            )
            .where(
                AcademyModality.academy_id == academy_id,
                Modality.is_active.is_(True),
            )
            .order_by(Modality.name)
        )

        stmt_result = await self.db_session.execute(stmt)
        modalities = stmt_result.mappings().all()

        return [ModalityRead(**dict(modality)) for modality in modalities]

    async def list_academy_options(
        self,
        academy_id: int,
    ) -> list[ModalityOptionRead]:
        modalities = await self.list_catalog()
        selected_modality_ids = await self.get_selected_modality_ids(
            academy_id
        )

        return [
            ModalityOptionRead(
                id=modality.id,
                name=modality.name,
                emoji=modality.emoji,
                is_selected=modality.id in selected_modality_ids,
            )
            for modality in modalities
        ]

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

    async def has_selected_modalities(
        self,
        academy_id: int,
    ) -> bool:
        total = await self.academy_modality_repository.count(
            filters=[
                AcademyModality.academy_id == academy_id,
            ],
        )

        return total > 0

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

    async def get_modality_by_name(
        self,
        name: str,
    ) -> ModalityRead | None:
        normalized_name = ' '.join(name.strip().split())

        modality = await self.modality_repository.get_one(
            filters=[
                func.lower(Modality.name) == normalized_name.lower(),
                Modality.is_active.is_(True),
            ],
        )

        if modality is None:
            return None

        return ModalityRead(**modality)
