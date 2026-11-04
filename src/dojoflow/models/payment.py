from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import (
    date_column,
    enum_column,
    int_fk,
    money_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import PaymentKind, PaymentStatus


class Payment(BaseModel):
    __tablename__ = 'payment'

    __table_args__ = (
        # Uma mensalidade (ou taxa) por matrícula e mês. A graduação fica
        # de fora: o mesmo aluno pode estar em duas listas no mesmo mês
        Index(
            'uq_payment_enrollment_kind_month',
            'academy_id',
            'enrollment_id',
            'kind',
            'reference_month',
            unique=True,
            postgresql_where=text("kind <> 'graduation'"),
        ),
    )

    academy_id: Mapped[int] = int_fk('academy.id')
    enrollment_id: Mapped[int] = int_fk('enrollment.id')

    kind: Mapped[PaymentKind] = enum_column(
        PaymentKind,
        default=PaymentKind.MONTHLY,
    )

    reference_month: Mapped[date] = date_column()
    due_date: Mapped[date | None] = date_column(nullable=True)

    status: Mapped[PaymentStatus] = enum_column(
        PaymentStatus,
        default=PaymentStatus.PENDING,
    )

    amount_due: Mapped[Decimal | None] = money_column(nullable=True)
    amount_paid: Mapped[Decimal] = money_column()

    paid_at: Mapped[date | None] = date_column(nullable=True)

    # Graduação: a entrada da lista que gerou a cobrança. Some (NULL) se o
    # aluno sai da lista depois de pagar; a cobrança paga continua
    graduation_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey('graduation_list_entry.id', ondelete='SET NULL'),
        nullable=True,
        unique=True,
    )
    # Graduação: o nome da faixa-alvo (ex.: "Verde"), guardado na cobrança
    description: Mapped[str | None] = str_column(length=120, nullable=True)
