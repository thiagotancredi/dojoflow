from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    big_int_column,
    enum_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.models.enums import (
    TelegramMessageDirection,
    TelegramMessageStatus,
)


class TelegramMessageLog(BaseModel):
    __tablename__ = 'telegram_message_log'

    academy_id: Mapped[int | None] = int_fk(
        'academy.id',
        nullable=True,
    )
    master_id: Mapped[int | None] = int_fk(
        'master.id',
        nullable=True,
    )
    student_id: Mapped[int | None] = int_fk(
        'student.id',
        nullable=True,
    )

    telegram_user_id: Mapped[int] = big_int_column(index=True)

    direction: Mapped[TelegramMessageDirection] = enum_column(
        TelegramMessageDirection,
        default=TelegramMessageDirection.INBOUND,
    )

    status: Mapped[TelegramMessageStatus] = enum_column(
        TelegramMessageStatus,
        default=TelegramMessageStatus.RECEIVED,
    )

    message_text: Mapped[str | None] = str_column(
        length=4000,
        nullable=True,
    )

    error_message: Mapped[str | None] = str_column(
        length=1000,
        nullable=True,
    )
