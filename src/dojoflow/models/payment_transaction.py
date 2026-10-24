from datetime import date
from decimal import Decimal

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import (
    date_column,
    enum_column,
    int_fk,
    money_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import PaymentMethod, PaymentSource


class PaymentTransaction(BaseModel):
    __tablename__ = 'payment_transaction'

    academy_id: Mapped[int] = int_fk('academy.id')
    student_id: Mapped[int] = int_fk('student.id')

    payment_method: Mapped[PaymentMethod | None] = enum_column(
        PaymentMethod,
        nullable=True,
    )

    gross_amount: Mapped[Decimal] = money_column()
    fee_amount: Mapped[Decimal | None] = money_column(nullable=True)
    net_amount: Mapped[Decimal | None] = money_column(nullable=True)

    received_at: Mapped[date] = date_column()

    notes: Mapped[str | None] = str_column(
        length=255,
        nullable=True,
    )

    # Manual (o mestre) ou automática (InfinitePay)
    source: Mapped[PaymentSource] = mapped_column(
        SQLEnum(
            PaymentSource,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            native_enum=False,
        ),
        default=PaymentSource.MANUAL,
        server_default=PaymentSource.MANUAL.value,
        nullable=False,
    )
