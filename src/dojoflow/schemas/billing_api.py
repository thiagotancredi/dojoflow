from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, field_validator

from dojoflow.schemas.billing import (
    AllocationPreview,
    AllocationRead,
    ChargeRead,
    ChargeStatus,
    PaymentRead,
    StudentBillingRead,
)
from dojoflow.shared.enums import PaymentKind, PaymentMethod


class ChargeApiRead(BaseModel):
    id: UUID
    kind: PaymentKind
    enrollment_id: UUID
    modality_name: str
    reference_month: date
    due_date: date
    amount: Decimal
    paid: Decimal
    status: ChargeStatus

    @classmethod
    def from_internal(cls, charge: ChargeRead) -> 'ChargeApiRead':
        return cls(
            id=charge.public_id,
            kind=charge.kind,
            enrollment_id=charge.enrollment_public_id,
            modality_name=charge.modality_name,
            reference_month=charge.reference_month,
            due_date=charge.due_date,
            amount=charge.amount,
            paid=charge.paid,
            status=charge.status,
        )


class AllocationApiRead(BaseModel):
    charge_id: UUID
    label: str
    amount: Decimal

    @classmethod
    def from_internal(cls, allocation: AllocationRead) -> 'AllocationApiRead':
        return cls(
            charge_id=allocation.charge_public_id,
            label=allocation.label,
            amount=allocation.amount,
        )


class PaymentApiRead(BaseModel):
    id: UUID
    amount: Decimal
    paid_on: date
    method: PaymentMethod | None
    notes: str | None
    allocations: list[AllocationApiRead]

    @classmethod
    def from_internal(cls, payment: PaymentRead) -> 'PaymentApiRead':
        return cls(
            id=payment.public_id,
            amount=payment.amount,
            paid_on=payment.paid_on,
            method=payment.method,
            notes=payment.notes,
            allocations=[
                AllocationApiRead.from_internal(item)
                for item in payment.allocations
            ],
        )


class StudentBillingApiRead(BaseModel):
    open_total: Decimal
    open_months: str
    whatsapp_url: str | None
    charges: list[ChargeApiRead]
    payments: list[PaymentApiRead]

    @classmethod
    def from_internal(
        cls, billing: StudentBillingRead
    ) -> 'StudentBillingApiRead':
        return cls(
            open_total=billing.open_total,
            open_months=billing.open_months,
            whatsapp_url=billing.whatsapp_url,
            charges=[ChargeApiRead.from_internal(c) for c in billing.charges],
            payments=[
                PaymentApiRead.from_internal(p) for p in billing.payments
            ],
        )


# Valor de cobrança: positivo, até 99.999.999,99 com 2 casas
Money = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=2),
    AfterValidator(lambda value: value.quantize(Decimal('0.01'))),
]
# Faixa de datas aceitável para cobranças (evita datas absurdas)
ChargeDate = Annotated[
    date,
    Field(ge=date(2000, 1, 1), le=date(2100, 12, 31)),
]


class LaunchChargeApiPayload(BaseModel):
    enrollment_id: UUID
    reference_month: ChargeDate
    amount: Money
    due_date: ChargeDate

    @field_validator('reference_month')
    @classmethod
    def _first_day(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError('reference_month must be the first day.')
        return value


class UpdateChargeApiPayload(BaseModel):
    amount: Money | None = None
    due_date: ChargeDate | None = None


class PaymentPreviewApiPayload(BaseModel):
    amount: Money


class AllocationPreviewApiRead(AllocationApiRead):
    settles: bool

    @classmethod
    def from_preview(
        cls, allocation: AllocationPreview
    ) -> 'AllocationPreviewApiRead':
        return cls(
            charge_id=allocation.charge_public_id,
            label=allocation.label,
            amount=allocation.amount,
            settles=allocation.settles,
        )


class PaymentPreviewApiRead(BaseModel):
    allocations: list[AllocationPreviewApiRead]


class CreatePaymentApiPayload(BaseModel):
    amount: Money
    paid_on: ChargeDate
    method: PaymentMethod | None = None
    notes: str | None = Field(default=None, max_length=255)
