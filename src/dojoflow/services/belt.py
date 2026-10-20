from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.belt import Belt
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.graduation_list import GraduationListEntry
from dojoflow.models.modality import Modality
from dojoflow.repositories.belt import BeltRepository
from dojoflow.schemas.belt import BeltPayload, BeltRead
from dojoflow.services.belt_presets import TAEKWONDO_NAME, TAEKWONDO_PRESET
from dojoflow.shared.exceptions import ConflictError, NotFoundError


def next_in_sequence(
    belts: list[BeltRead],
    current_belt_id: int | None,
) -> BeltRead | None:
    """Próxima faixa da sequência; sem faixa atual, a primeira."""
    if current_belt_id is None:
        return belts[0] if belts else None

    ids = [belt.id for belt in belts]

    if current_belt_id not in ids:
        return None

    index = ids.index(current_belt_id) + 1

    return belts[index] if index < len(belts) else None


class BeltService:
    def __init__(
        self,
        belt_repository: BeltRepository,
        db_session: AsyncSession,
    ) -> None:
        self.belt_repository = belt_repository
        self.db_session = db_session

    async def list_by_modality(
        self,
        academy_id: int,
        modality_id: int,
    ) -> list[BeltRead]:
        belts = await self.belt_repository.list(
            filters=[
                Belt.academy_id == academy_id,
                Belt.modality_id == modality_id,
            ],
            order_by=[Belt.position, Belt.id],
        )

        return [BeltRead(**belt) for belt in belts]

    async def get(self, academy_id: int, belt_id: int) -> BeltRead:
        belt = await self.belt_repository.get_one(
            filters=[Belt.id == belt_id, Belt.academy_id == academy_id],
        )

        if belt is None:
            raise NotFoundError(
                'Could not find this belt.',
                code='BELT_NOT_FOUND',
            )

        return BeltRead(**belt)

    async def next_belt(
        self,
        academy_id: int,
        modality_id: int,
        current_belt_id: int | None,
    ) -> BeltRead | None:
        belts = await self.list_by_modality(academy_id, modality_id)

        return next_in_sequence(belts, current_belt_id)

    @transactional
    async def create(
        self,
        academy_id: int,
        modality_id: int,
        data: BeltPayload,
    ) -> BeltRead:
        await self._ensure_name_is_free(academy_id, modality_id, data.name)

        last_position = await self.db_session.scalar(
            select(func.max(Belt.position)).where(
                Belt.academy_id == academy_id,
                Belt.modality_id == modality_id,
            )
        )

        belt_id = await self.belt_repository.create({
            **data.model_dump(),
            'academy_id': academy_id,
            'modality_id': modality_id,
            'position': (last_position or 0) + 1,
        })

        return await self.get(academy_id, belt_id)

    @transactional
    async def update(
        self,
        academy_id: int,
        belt_id: int,
        data: BeltPayload,
    ) -> BeltRead:
        belt = await self.get(academy_id, belt_id)
        await self._ensure_name_is_free(
            academy_id,
            belt.modality_id,
            data.name,
            ignore_belt_id=belt_id,
        )

        await self.belt_repository.update_by_id(belt_id, data)

        return await self.get(academy_id, belt_id)

    @transactional
    async def delete(self, academy_id: int, belt_id: int) -> None:
        belt = await self.get(academy_id, belt_id)

        if await self._is_in_use(belt_id):
            raise ConflictError(
                "This belt is used in a student's history or in a "
                'graduation list.',
                code='BELT_IN_USE',
            )

        await self.belt_repository.delete_by_id(belt_id)

        remaining = await self.list_by_modality(academy_id, belt.modality_id)
        await self._renumber([item.id for item in remaining])

    @transactional
    async def reorder(
        self,
        academy_id: int,
        modality_id: int,
        belt_ids: list[int],
    ) -> None:
        current = await self.list_by_modality(academy_id, modality_id)
        current_ids = [belt.id for belt in current]

        if len(belt_ids) != len(set(belt_ids)) or sorted(belt_ids) != sorted(
            current_ids
        ):
            raise ConflictError(
                'The new order must list every belt of this modality once.',
                code='BELT_ORDER_MISMATCH',
            )

        await self._renumber(belt_ids)

    @transactional
    async def apply_taekwondo_preset(
        self,
        academy_id: int,
        modality_id: int,
    ) -> list[BeltRead]:
        modality_name = await self.db_session.scalar(
            select(Modality.name).where(Modality.id == modality_id)
        )

        if modality_name != TAEKWONDO_NAME:
            raise ConflictError(
                'The default sequence is only available for Taekwondo.',
                code='PRESET_NOT_AVAILABLE',
            )

        if await self.list_by_modality(academy_id, modality_id):
            raise ConflictError(
                'This modality already has belts.',
                code='BELTS_ALREADY_EXIST',
            )

        for payload in TAEKWONDO_PRESET:
            await self.create(academy_id, modality_id, payload)

        return await self.list_by_modality(academy_id, modality_id)

    async def _renumber(self, ordered_ids: list[int]) -> None:
        for position, belt_id in enumerate(ordered_ids, 1):
            await self.belt_repository.update_by_id(
                belt_id, {'position': position}
            )

    async def _ensure_name_is_free(
        self,
        academy_id: int,
        modality_id: int,
        name: str,
        ignore_belt_id: int | None = None,
    ) -> None:
        filters = [
            Belt.academy_id == academy_id,
            Belt.modality_id == modality_id,
            func.lower(Belt.name) == name.lower(),
        ]

        if ignore_belt_id is not None:
            filters.append(Belt.id != ignore_belt_id)

        if await self.belt_repository.exists(filters=filters):
            raise ConflictError(
                'There is already a belt with this name in this modality.',
                code='BELT_NAME_TAKEN',
            )

    async def _is_in_use(self, belt_id: int) -> bool:
        in_history = await self.db_session.scalar(
            select(EnrollmentBelt.id)
            .where(EnrollmentBelt.belt_id == belt_id)
            .limit(1)
        )

        if in_history is not None:
            return True

        in_list = await self.db_session.scalar(
            select(GraduationListEntry.id)
            .where(
                (GraduationListEntry.target_belt_id == belt_id)
                | (GraduationListEntry.snapshot_belt_id == belt_id)
            )
            .limit(1)
        )

        return in_list is not None
