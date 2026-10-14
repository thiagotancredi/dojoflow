from datetime import datetime
from typing import NamedTuple

from pydantic import BaseModel, Field, field_validator

from dojoflow.schemas.master_context import MasterContextRead


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


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    master: MasterContextRead


class AuthResult(NamedTuple):
    response: AuthTokenResponse
    refresh_token: str


class TelegramLinkTokenResponse(BaseModel):
    token: str
    deep_link: str | None = None
    expires_at: datetime


class SetCredentialsRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    setup_token: str | None = Field(default=None, min_length=10)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()

        if '@' not in normalized or '.' not in normalized.split('@')[-1]:
            raise ValueError('Invalid email format.')

        return normalized


class TelegramSetupTokenResponse(BaseModel):
    token: str
    expires_at: datetime
