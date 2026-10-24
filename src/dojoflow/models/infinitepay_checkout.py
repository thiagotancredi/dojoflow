from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    datetime_column,
    enum_column,
    int_column,
    int_fk,
    money_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import CheckoutStatus


class InfinitePayCheckout(BaseModel):
    """Link de checkout da InfinitePay criado para um aluno pagar."""

    __tablename__ = 'infinitepay_checkout'

    academy_id: Mapped[int] = int_fk('academy.id')
    student_id: Mapped[int] = int_fk('student.id')
    # Tag com que o link foi criado: a conferência usa esta, mesmo que o
    # mestre troque a tag ou desligue depois
    handle: Mapped[str] = str_column(length=60)
    # Nosso número do pedido: aleatório e impossível de adivinhar
    order_nsu: Mapped[str] = str_column(length=64, unique=True)
    amount: Mapped[Decimal] = money_column()
    url: Mapped[str] = str_column(length=1000)
    status: Mapped[CheckoutStatus] = enum_column(
        CheckoutStatus, default=CheckoutStatus.OPEN
    )

    # Preenchidos quando o pagamento é conferido
    transaction_nsu: Mapped[str | None] = str_column(
        length=64, nullable=True, unique=True
    )
    invoice_slug: Mapped[str | None] = str_column(length=64, nullable=True)
    receipt_url: Mapped[str | None] = str_column(length=500, nullable=True)
    capture_method: Mapped[str | None] = str_column(length=20, nullable=True)
    paid_amount: Mapped[Decimal | None] = money_column(nullable=True)
    installments: Mapped[int | None] = int_column(nullable=True)
    paid_at: Mapped[datetime | None] = datetime_column(nullable=True)
    payment_transaction_id: Mapped[int | None] = int_fk(
        'payment_transaction.id', nullable=True
    )
