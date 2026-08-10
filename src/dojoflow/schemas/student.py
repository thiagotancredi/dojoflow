from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import (
    EnrollmentStatus,
    StudentResponsibleRelationship,
    StudentSex,
)


class StudentCreate(BaseModel):
    academy_id: int = Field(gt=0)
    address_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    phone_is_whatsapp: bool | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    instagram: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None
    sex: StudentSex | None = None


class StudentRead(ReadBase):
    academy_id: int
    address_id: int | None
    name: str
    phone: str | None
    phone_is_whatsapp: bool | None
    cpf: str | None
    instagram: str | None
    email: str | None
    birth_date: date | None
    sex: StudentSex | None


class StudentAddressPayload(BaseModel):
    zip_code: str | None = Field(default=None, min_length=8, max_length=8)
    street: str | None = Field(default=None, max_length=160)
    neighborhood: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    number: str | None = Field(default=None, max_length=20)
    complement: str | None = Field(default=None, max_length=120)


class StudentResponsiblePayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    phone_is_whatsapp: bool = False
    email: str | None = Field(default=None, max_length=255)
    relationship: StudentResponsibleRelationship


class StudentResponsibleReferencePayload(BaseModel):
    responsible_id: int = Field(gt=0)
    relationship: StudentResponsibleRelationship


class StudentEnrollmentPayload(BaseModel):
    modality_id: int = Field(gt=0)
    monthly_fee: Decimal = Field(ge=0)
    due_day: int = Field(ge=1, le=31)
    is_exempt: bool = False
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class StudentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    phone_is_whatsapp: bool | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    instagram: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None
    sex: StudentSex | None = None
    enrollment: StudentEnrollmentPayload
    address: StudentAddressPayload | None = None
    address_reference_student_id: int | None = Field(default=None, gt=0)
    responsibles: list[StudentResponsiblePayload] = Field(default_factory=list)
    responsible_references: list[StudentResponsibleReferencePayload] = Field(
        default_factory=list
    )


class StudentBasicUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    phone_is_whatsapp: bool | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    instagram: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None
    sex: StudentSex | None = None


class StudentEnrollmentUpdateRequest(BaseModel):
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=1, le=31)
    is_exempt: bool | None = None
    status: EnrollmentStatus | None = None


class StudentModalityUpdateRequest(BaseModel):
    modality_id: int = Field(gt=0)


class StudentDetailsRead(BaseModel):
    student: StudentRead
    enrollments: list[dict[str, Any]]
    address: dict[str, Any] | None
    responsibles: list[dict[str, Any]]
