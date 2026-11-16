import secrets
from datetime import date
from decimal import Decimal

from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import (
    bool_column,
    date_column,
    enum_column,
    int_fk,
    money_column,
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
    # Valor do link de pagamento que o mestre gerou ("Cobrar"); NULL = o
    # total em aberto. Volta a NULL na virada do mês
    pay_amount: Mapped[Decimal | None] = money_column(nullable=True)
    # Mês (dia 1) a que o link atual pertence: na virada, quem ainda está
    # com o link do mês anterior ganha um novo (uma vez por mês)
    pay_link_month: Mapped[date] = mapped_column(
        nullable=False,
        server_default=text("date_trunc('month', current_date)::date"),
    )
    # Link da graduação: próprio, para não cair quando o "Cobrar" da
    # mensalidade troca o pay_token
    graduation_pay_token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=new_pay_token,
    )
