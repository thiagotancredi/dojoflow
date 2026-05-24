from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.repositories.master import MasterRepository
from dojoflow.schemas.master import MasterCreate
from dojoflow.schemas.master_context import MasterContextRead


class MasterService:
    def __init__(
        self,
        master_repository: MasterRepository,
        db_session: AsyncSession,
    ) -> None:
        self.master_repository = master_repository
        self.db_session = db_session

    @transactional
    async def create(self, data: MasterCreate) -> int:
        return await self.master_repository.create(data.model_dump())

    async def get_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        return await self.master_repository.get_by_telegram_user_id(
            telegram_user_id
        )

    async def get_context_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> MasterContextRead | None:
        context = await self.master_repository.get_context_by_telegram_user_id(
            telegram_user_id
        )

        if context is None:
            return None

        return MasterContextRead(**context)
