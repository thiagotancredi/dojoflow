from decimal import Decimal

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import int_fk, money_column
from dojoflow.models.base_model import BaseModel


class PaymentAllocation(BaseModel):
    __tablename__ = 'payment_allocation'

    __table_args__ = (
        UniqueConstraint(
            'academy_id',
            'payment_transaction_id',
            'payment_id',
            name='uq_payment_allocation_transaction_payment',
        ),
    )

    academy_id: Mapped[int] = int_fk('academy.id')

    payment_transaction_id: Mapped[int] = int_fk('payment_transaction.id')
    payment_id: Mapped[int] = int_fk('payment.id')

    allocated_amount: Mapped[Decimal] = money_column()
