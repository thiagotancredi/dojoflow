from datetime import date, datetime
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
    student_id: int
    enrollment_public_id: UUID
    modality_name: str
    reference_month: date
    due_date: date
    amount: Decimal
    paid: Decimal
    status: ChargeStatus
    created_at: datetime

    @property
    def open_amount(self) -> Decimal:
        return self.amount - self.paid


class AllocationRead(BaseModel):
    charge_public_id: UUID
    label: str
    amount: Decimal


class AllocationPreview(AllocationRead):
    settles: bool


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
    pay_url: str
    charges: list[ChargeRead]
    payments: list[PaymentRead]


OverviewFilter = Literal['overdue', 'upcoming', 'paid', 'all']


class BillingOverviewItemRead(BaseModel):
    student_id: UUID
    name: str
    # Preenchido quando a cobrança vai para o responsável (aluno menor)
    responsible_name: str | None
    modalities: list[str]
    open_amount: Decimal
    days_late: int | None
    whatsapp_url: str | None


class BillingOverviewRead(BaseModel):
    month_expected: Decimal
    month_received: Decimal
    overdue_total: Decimal
    overdue_students: int
    due_soon_total: Decimal
    due_soon_students: int
    items: list[BillingOverviewItemRead]
    total: int
    page: int
    page_size: int
