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
    # Nome completo de quem recebe a mensagem (aluno ou responsável)
    greeting_name: str
    status: Literal['open', 'clear']
    items: list[PublicPaymentItemRead]
    total: Decimal
    recipient_name: str
    # Pix copia e cola com o valor; None sem dívida, sem dados de Pix ou
    # com a baixa automática ligada
    pix_code: str | None
    # Baixa automática ligada: a página mostra "Pagar mensalidade", que
    # leva ao checkout da InfinitePay
    checkout_enabled: bool = False


class PublicCheckoutRead(BaseModel):
    """Endereço do checkout da InfinitePay para onde o aluno vai."""

    url: str
