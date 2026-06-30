from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import int_fk, str_column
from dojoflow.models.base_model import BaseModel


class Address(BaseModel):
    __tablename__ = 'address'

    academy_id: Mapped[int] = int_fk('academy.id')

    zip_code: Mapped[str | None] = str_column(length=8, nullable=True)
    street: Mapped[str | None] = str_column(length=160, nullable=True)
    neighborhood: Mapped[str | None] = str_column(length=120, nullable=True)
    city: Mapped[str | None] = str_column(length=120, nullable=True)
    state: Mapped[str | None] = str_column(length=2, nullable=True)
    number: Mapped[str | None] = str_column(length=20, nullable=True)
    complement: Mapped[str | None] = str_column(length=120, nullable=True)
