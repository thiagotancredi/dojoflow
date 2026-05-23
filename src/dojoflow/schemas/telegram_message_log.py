from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import (
    TelegramMessageDirection,
    TelegramMessageStatus,
)


class TelegramMessageLogCreate(BaseModel):
    academy_id: int | None = Field(default=None, gt=0)
    master_id: int | None = Field(default=None, gt=0)
    student_id: int | None = Field(default=None, gt=0)
    telegram_user_id: int = Field(gt=0)
    direction: TelegramMessageDirection
    status: TelegramMessageStatus
    message_text: str | None = Field(default=None, max_length=4000)
    error_message: str | None = Field(default=None, max_length=1000)


class TelegramMessageLogRead(ReadBase):
    academy_id: int | None
    master_id: int | None
    student_id: int | None
    telegram_user_id: int
    direction: TelegramMessageDirection
    status: TelegramMessageStatus
    message_text: str | None
    error_message: str | None
