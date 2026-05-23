from typing import Any

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    big_int_column,
    int_fk,
    json_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class TelegramConversationState(BaseModel):
    __tablename__ = 'telegram_conversation_state'

    telegram_user_id: Mapped[int] = big_int_column(
        unique=True,
        index=True,
    )

    academy_id: Mapped[int | None] = int_fk(
        'academy.id',
        nullable=True,
    )
    master_id: Mapped[int | None] = int_fk(
        'master.id',
        nullable=True,
    )

    current_flow: Mapped[str | None] = str_column(
        length=80,
        nullable=True,
    )
    current_step: Mapped[str | None] = str_column(
        length=80,
        nullable=True,
    )

    context_data: Mapped[dict[str, Any]] = json_column()
