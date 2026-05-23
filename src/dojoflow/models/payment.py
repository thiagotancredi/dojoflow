from datetime import date
from decimal import Decimal

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    date_column,
    enum_column,
    int_fk,
    money_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import PaymentStatus


class Payment(BaseModel):
    __tablename__ = 'payment'

    __table_args__ = (
        UniqueConstraint(
            'academy_id',
            'enrollment_id',
            'reference_month',
            name='uq_payment_academy_enrollment_reference_month',
        ),
    )

    academy_id: Mapped[int] = int_fk('academy.id')
    enrollment_id: Mapped[int] = int_fk('enrollment.id')

    reference_month: Mapped[date] = date_column()
    due_date: Mapped[date | None] = date_column(nullable=True)

    status: Mapped[PaymentStatus] = enum_column(
        PaymentStatus,
        default=PaymentStatus.PENDING,
    )

    amount_due: Mapped[Decimal | None] = money_column(nullable=True)
    amount_paid: Mapped[Decimal] = money_column()

    paid_at: Mapped[date | None] = date_column(nullable=True)
