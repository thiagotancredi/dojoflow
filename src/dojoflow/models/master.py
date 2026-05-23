from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    big_int_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class Master(BaseModel):
    __tablename__ = 'master'

    academy_id: Mapped[int] = int_fk('academy.id')

    telegram_user_id: Mapped[int] = big_int_column(
        unique=True,
        index=True,
    )

    name: Mapped[str] = str_column(length=120)
    phone: Mapped[str | None] = str_column(length=20, nullable=True)
