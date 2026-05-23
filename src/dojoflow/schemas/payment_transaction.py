from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import PaymentMethod


class PaymentTransactionCreate(BaseModel):
    academy_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    payment_method: PaymentMethod = PaymentMethod.PIX
    gross_amount: Decimal = Field(gt=0)
    fee_amount: Decimal | None = Field(default=None, ge=0)
    net_amount: Decimal | None = Field(default=None, ge=0)
    received_at: date
    notes: str | None = Field(default=None, max_length=255)


class PaymentTransactionRead(ReadBase):
    academy_id: int
    student_id: int
    payment_method: PaymentMethod
    gross_amount: Decimal
    fee_amount: Decimal | None
    net_amount: Decimal | None
    received_at: date
    notes: str | None
