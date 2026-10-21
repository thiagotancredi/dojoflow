from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from dojoflow.shared.enums import PaymentKind, PaymentMethod

ChargeStatus = Literal['paid', 'partial', 'overdue', 'upcoming', 'waived']


class ChargeRead(BaseModel):
    """Cobrança (mensalidade ou taxa) como a ficha do aluno mostra."""

    id: int
    public_id: UUID
    kind: PaymentKind
    enrollment_public_id: UUID
    modality_name: str
    reference_month: date
    due_date: date
    amount: Decimal
    paid: Decimal
    status: ChargeStatus


class AllocationRead(BaseModel):
    charge_public_id: UUID
    label: str
    amount: Decimal


class PaymentRead(BaseModel):
    """Uma baixa e para onde o dinheiro foi."""

    id: int
    public_id: UUID
    amount: Decimal
    paid_on: date
    method: PaymentMethod | None
    notes: str | None
    allocations: list[AllocationRead]


class StudentBillingRead(BaseModel):
    open_total: Decimal
    open_months: str
    whatsapp_url: str | None
    charges: list[ChargeRead]
    payments: list[PaymentRead]
