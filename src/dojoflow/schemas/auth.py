from datetime import datetime
from typing import NamedTuple

from pydantic import BaseModel, Field, field_validator


class AuthRegisterRequest(BaseModel):
    academy_name: str = Field(min_length=2, max_length=120)
    master_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()

        if '@' not in normalized or '.' not in normalized.split('@')[-1]:
            raise ValueError('Invalid email format.')

        return normalized


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


# Só a sessão; quem é o usuário vem de GET /auth/me.
class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class AuthResult(NamedTuple):
    response: AuthTokenResponse
    refresh_token: str


class SetCredentialsRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    current_password: str | None = Field(default=None, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()

        if '@' not in normalized or '.' not in normalized.split('@')[-1]:
            raise ValueError('Invalid email format.')

        return normalized


class SupportEntryRead(BaseModel):
    code: str
    expires_at: datetime


class SupportExchangeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
