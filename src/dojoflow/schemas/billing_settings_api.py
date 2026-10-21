from pydantic import BaseModel, Field, field_validator


class BillingSettingsApi(BaseModel):
    """Dados de cobrança da academia (Configurações → Cobrança)."""

    pix_key: str | None = Field(default=None, max_length=140)
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
