from typing import Any

from dojoflow.models.telegram_conversation_state import (
    TelegramConversationState,
)
from dojoflow.repositories.base import BaseRepository


class TelegramConversationStateRepository(
    BaseRepository[TelegramConversationState]
):
    async def get_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        return await self.get_one(
            filters=[
                TelegramConversationState.telegram_user_id == telegram_user_id
            ],
        )
