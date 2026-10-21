from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from dojoflow.shared.enums import AcademyStatus


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()

    if '@' not in normalized or '.' not in normalized.split('@')[-1]:
        raise ValueError('Invalid email format.')

    return normalized


class AdminMasterRead(BaseModel):
    id: UUID
    name: str
    email: str | None
    phone: str | None


class AdminAcademyRead(BaseModel):
    id: UUID
    name: str
    status: AcademyStatus
    created_at: datetime
    master: AdminMasterRead | None
    # Academia do próprio administrador (não pode ser desativada)
    is_own: bool


class AdminAcademyCreate(BaseModel):
    academy_name: str = Field(min_length=2, max_length=120)
    master_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


class AdminCredentialsRead(BaseModel):
    academy: AdminAcademyRead
    password: str
