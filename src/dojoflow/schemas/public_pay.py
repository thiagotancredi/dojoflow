from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class PublicPaymentItemRead(BaseModel):
    label: str
    amount: Decimal


class PublicPaymentRead(BaseModel):
    """Página pública de pagamento: só o que o aluno precisa ver."""

    academy_name: str
    master_name: str
    # Primeiro nome de quem recebe a mensagem (aluno ou responsável)
    greeting_name: str
    status: Literal['open', 'clear']
    items: list[PublicPaymentItemRead]
    total: Decimal
    recipient_name: str
    # Pix copia e cola com o valor; None sem dívida ou sem dados de Pix
    pix_code: str | None
