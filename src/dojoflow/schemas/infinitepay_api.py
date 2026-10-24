from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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
