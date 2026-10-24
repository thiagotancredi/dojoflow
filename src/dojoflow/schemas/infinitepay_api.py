from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InfinitePayStatusApi(BaseModel):
    """Situação da baixa automática (a chave nunca volta, só o final)."""

    enabled: bool
    handle: str | None
    tested_at: datetime | None
    key_last4: str | None


class InfinitePayConnectApi(BaseModel):
    """Testar e ligar: InfiniteTag (com ou sem $) e a chave de API."""

    handle: str = Field(min_length=1, max_length=60)
    api_key: str = Field(min_length=1, max_length=200)

    @field_validator('handle', mode='before')
    @classmethod
    def _normalize_handle(cls, value: object) -> object:
        # "$KatsuFlow " → "katsuflow"
        if isinstance(value, str):
            return ''.join(value.replace('$', '').split()).lower()
        return value

    @field_validator('api_key', mode='before')
    @classmethod
    def _strip_key(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


def _infinitepay_receipt(value: str | None) -> str | None:
    """Recibo vem de quem chamou a rota (sem login): só fica se for um
    endereço https da própria InfinitePay; senão é descartado."""
    if not value:
        return None
    parts = urlsplit(value)
    host = (parts.hostname or '').lower()
    trusted = host == 'infinitepay.io' or host.endswith('.infinitepay.io')
    return value if parts.scheme == 'https' and trusted else None


class InfinitePayWebhookApi(BaseModel):
    """Aviso de pagamento da InfinitePay (só o que a conferência usa)."""

    model_config = ConfigDict(extra='ignore')

    order_nsu: str = Field(min_length=1, max_length=64)
    transaction_nsu: str = Field(min_length=1, max_length=64)
    invoice_slug: str = Field(min_length=1, max_length=64)
    receipt_url: str | None = Field(default=None, max_length=500)

    @field_validator('receipt_url')
    @classmethod
    def _trusted_receipt(cls, value: str | None) -> str | None:
        return _infinitepay_receipt(value)


class PayConfirmApi(BaseModel):
    """Volta do aluno do checkout (a InfinitePay acrescenta ao endereço)."""

    order_nsu: str = Field(min_length=1, max_length=64)
    transaction_nsu: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=64)
    receipt_url: str | None = Field(default=None, max_length=500)

    @field_validator('receipt_url')
    @classmethod
    def _trusted_receipt(cls, value: str | None) -> str | None:
        return _infinitepay_receipt(value)


class PayConfirmRead(BaseModel):
    status: Literal['processing']


class WebhookAckRead(BaseModel):
    received: Literal[True] = True
