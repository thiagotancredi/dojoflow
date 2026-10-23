from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from dojoflow.services.pix import normalize_pix_key
from dojoflow.shared.enums import PixKeyType


class BillingSettingsApi(BaseModel):
    """Dados de cobrança da academia (Configurações → Cobrança)."""

    pix_key: str | None = Field(default=None, max_length=140)
    pix_key_type: PixKeyType | None = None
    pix_city: str | None = Field(default=None, max_length=60)
    recipient_name: str | None = Field(default=None, max_length=120)
    bank_details: str | None = Field(default=None, max_length=500)
    message_template: str | None = Field(default=None, max_length=1000)

    @field_validator('*', mode='before')
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode='after')
    def _key_matches_type(self) -> Self:
        # Sem chave, o tipo não vale nada; com chave, o tipo é obrigatório
        # e a chave fica guardada no formato do código Pix
        if self.pix_key is None:
            self.pix_key_type = None
            return self
        if self.pix_key_type is None:
            raise ValueError('Escolha o tipo da chave Pix.')
        self.pix_key = normalize_pix_key(self.pix_key, self.pix_key_type)
        return self
