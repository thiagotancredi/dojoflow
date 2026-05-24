from typing import Any

from dojoflow.models.master import Master
from dojoflow.repositories.base import BaseRepository


class MasterRepository(BaseRepository[Master]):
    async def get_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        return await self.get_one(
            filters=[Master.telegram_user_id == telegram_user_id],
        )
