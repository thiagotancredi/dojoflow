import secrets
from datetime import date

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import (
    bool_column,
    date_column,
    enum_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import StudentSex


def new_pay_token() -> str:
    """Código secreto do link de pagamento do aluno (/pagar/<código>)."""
    return secrets.token_urlsafe(16)


class Student(BaseModel):
    __tablename__ = 'student'

    academy_id: Mapped[int] = int_fk('academy.id')
    address_id: Mapped[int | None] = int_fk('address.id', nullable=True)

    name: Mapped[str] = str_column(length=120)

    phone: Mapped[str | None] = str_column(length=20, nullable=True)
    phone_is_whatsapp: Mapped[bool | None] = bool_column(
        nullable=True,
    )
    cpf: Mapped[str | None] = str_column(length=11, nullable=True)
    instagram: Mapped[str | None] = str_column(length=80, nullable=True)
    email: Mapped[str | None] = str_column(length=255, nullable=True)

    birth_date: Mapped[date | None] = date_column(nullable=True)

    sex: Mapped[StudentSex | None] = enum_column(
        StudentSex,
        nullable=True,
    )

    pay_token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=new_pay_token,
    )
