from typing import Any

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase


class TelegramConversationStateCreate(BaseModel):
    telegram_user_id: int = Field(gt=0)
    academy_id: int | None = Field(default=None, gt=0)
    master_id: int | None = Field(default=None, gt=0)
    current_flow: str | None = Field(default=None, max_length=80)
    current_step: str | None = Field(default=None, max_length=80)
    context_data: dict[str, Any] = Field(default_factory=dict)


class TelegramConversationStateRead(ReadBase):
    telegram_user_id: int
    academy_id: int | None
    master_id: int | None
    current_flow: str | None
    current_step: str | None
    context_data: dict[str, Any]
