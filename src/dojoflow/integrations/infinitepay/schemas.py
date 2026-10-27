from decimal import Decimal

from pydantic import BaseModel


class CheckoutItem(BaseModel):
    description: str
    quantity: int = 1
    # Em reais; o cliente converte para centavos
    price: Decimal


class CheckoutCustomer(BaseModel):
    name: str
    # No formato +55DDDNÚMERO
    phone_number: str | None = None
    email: str | None = None


class PaymentCheck(BaseModel):
    """Resposta do payment_check, com valores já em reais."""

    success: bool
    paid: bool
    amount: Decimal | None = None
    paid_amount: Decimal | None = None
    capture_method: str | None = None
    installments: int | None = None
