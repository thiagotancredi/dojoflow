from pydantic import BaseModel, Field, field_validator


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class PasswordResetRequestRead(BaseModel):
    status: str = 'sent'


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
