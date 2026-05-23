from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    date_column,
    enum_column,
    int_fk,
    money_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import PaymentMethod


class PaymentTransaction(BaseModel):
    __tablename__ = 'payment_transaction'

    academy_id: Mapped[int] = int_fk('academy.id')
    student_id: Mapped[int] = int_fk('student.id')

    payment_method: Mapped[PaymentMethod] = enum_column(
        PaymentMethod,
        default=PaymentMethod.PIX,
    )

    gross_amount: Mapped[Decimal] = money_column()
    fee_amount: Mapped[Decimal | None] = money_column(nullable=True)
    net_amount: Mapped[Decimal | None] = money_column(nullable=True)

    received_at: Mapped[date] = date_column()

    notes: Mapped[str | None] = str_column(
        length=255,
        nullable=True,
    )
