from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import PaymentStatus


class PaymentCreate(BaseModel):
    academy_id: int = Field(gt=0)
    enrollment_id: int = Field(gt=0)
    reference_month: date
    due_date: date | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    amount_due: Decimal | None = Field(default=None, ge=0)
    amount_paid: Decimal = Field(default=Decimal('0.00'), ge=0)
    paid_at: date | None = None


class PaymentRead(ReadBase):
    academy_id: int
    enrollment_id: int
    reference_month: date
    due_date: date | None
    status: PaymentStatus
    amount_due: Decimal | None
    amount_paid: Decimal
    paid_at: date | None
