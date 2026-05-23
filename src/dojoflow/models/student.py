from datetime import date

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    date_column,
    enum_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.models.enums import StudentSex


class Student(BaseModel):
    __tablename__ = 'student'

    academy_id: Mapped[int] = int_fk('academy.id')

    name: Mapped[str] = str_column(length=120)

    phone: Mapped[str | None] = str_column(length=20, nullable=True)
    cpf: Mapped[str | None] = str_column(length=11, nullable=True)
    instagram: Mapped[str | None] = str_column(length=80, nullable=True)

    birth_date: Mapped[date | None] = date_column(nullable=True)

    sex: Mapped[StudentSex | None] = enum_column(
        StudentSex,
        nullable=True,
    )
