from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from dojoflow.schemas.student import (
    StudentAddressPayload,
    StudentResponsiblePayload,
)
from dojoflow.shared.enums import (
    EnrollmentStatus,
    StudentResponsibleRelationship,
    StudentSex,
)

MIN_DUE_DAY = 1
MAX_DUE_DAY = 28


class StudentApiRead(BaseModel):
    id: UUID
    name: str
    phone: str | None
    phone_is_whatsapp: bool | None
    cpf: str | None
    instagram: str | None
    email: str | None
    birth_date: date | None
    sex: StudentSex | None
    created_at: datetime

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> 'StudentApiRead':
        fields = {
            name: record[name] for name in cls.model_fields if name != 'id'
        }

        return cls(id=record['public_id'], **fields)


class AddressApiRead(BaseModel):
    zip_code: str | None
    street: str | None
    neighborhood: str | None
    city: str | None
    state: str | None
    number: str | None
    complement: str | None


class EnrollmentApiRead(BaseModel):
    id: UUID
    modality_id: UUID
    modality_name: str
    status: EnrollmentStatus
    monthly_fee: Decimal | None
    due_day: int | None
    is_exempt: bool


class ResponsibleLinkApiRead(BaseModel):
    id: UUID
    responsible_id: UUID
    name: str
    phone: str | None
    phone_is_whatsapp: bool | None
    email: str | None
    relationship: StudentResponsibleRelationship


class StudentDetailRead(BaseModel):
    student: StudentApiRead
    address: AddressApiRead | None
    responsibles: list[ResponsibleLinkApiRead]
    enrollments: list[EnrollmentApiRead]

    @classmethod
    def from_details(cls, details: Mapping[str, Any]) -> 'StudentDetailRead':
        address = details['address']

        return cls(
            student=StudentApiRead.from_record(details['student']),
            address=AddressApiRead(**address) if address else None,
            responsibles=[
                ResponsibleLinkApiRead(
                    id=item['link_public_id'],
                    responsible_id=item['responsible_public_id'],
                    name=item['name'],
                    phone=item['phone'],
                    phone_is_whatsapp=item['phone_is_whatsapp'],
                    email=item['email'],
                    relationship=item['relationship'],
                )
                for item in details['responsibles']
            ],
            enrollments=[
                EnrollmentApiRead(
                    id=item['enrollment_public_id'],
                    modality_id=item['modality_public_id'],
                    modality_name=item['modality_name'],
                    status=item['status'],
                    monthly_fee=item['monthly_fee'],
                    due_day=item['due_day'],
                    is_exempt=item['is_exempt'],
                )
                for item in details['enrollments']
            ],
        )


class EnrollmentApiPayload(BaseModel):
    modality_id: UUID
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=MIN_DUE_DAY, le=MAX_DUE_DAY)
    is_exempt: bool = False
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class StudentCreateApiRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    phone_is_whatsapp: bool | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    instagram: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None
    sex: StudentSex | None = None
    enrollment: EnrollmentApiPayload
    address: StudentAddressPayload | None = None
    responsibles: list[StudentResponsiblePayload] = Field(default_factory=list)


class EnrollmentApiUpdateRequest(BaseModel):
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=MIN_DUE_DAY, le=MAX_DUE_DAY)
    is_exempt: bool | None = None
    status: EnrollmentStatus | None = None

    @field_validator('status', 'is_exempt', mode='before')
    @classmethod
    def _reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError('This field cannot be null.')

        return value
