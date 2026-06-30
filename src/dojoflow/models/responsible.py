from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    bool_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class Responsible(BaseModel):
    __tablename__ = 'responsible'

    academy_id: Mapped[int] = int_fk('academy.id')

    name: Mapped[str] = str_column(length=120)
    phone: Mapped[str] = str_column(length=20)
    phone_is_whatsapp: Mapped[bool] = bool_column(default=False)
    email: Mapped[str | None] = str_column(length=255, nullable=True)
