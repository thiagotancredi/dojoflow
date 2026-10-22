from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class Master(BaseModel):
    __tablename__ = 'master'

    academy_id: Mapped[int] = int_fk('academy.id')

    email: Mapped[str | None] = str_column(
        length=255,
        nullable=True,
        unique=True,
        index=True,
    )
    password_hash: Mapped[str | None] = str_column(
        length=255,
        nullable=True,
    )

    name: Mapped[str] = str_column(length=120)
    phone: Mapped[str | None] = str_column(length=20, nullable=True)
