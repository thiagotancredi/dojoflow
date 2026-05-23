from decimal import Decimal

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase


class PaymentAllocationCreate(BaseModel):
    academy_id: int = Field(gt=0)
    payment_transaction_id: int = Field(gt=0)
    payment_id: int = Field(gt=0)
    allocated_amount: Decimal = Field(gt=0)


class PaymentAllocationRead(ReadBase):
    academy_id: int
    payment_transaction_id: int
    payment_id: int
    allocated_amount: Decimal
