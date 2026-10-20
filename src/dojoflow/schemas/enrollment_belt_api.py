from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from dojoflow.schemas.belt_api import BeltApiRead
from dojoflow.schemas.enrollment_belt import (
    BeltRecord,
    PendingBeltEnrollment,
)
from dojoflow.shared.enums import Eligibility

# Faixa de datas aceitável para uma graduação (evita datas absurdas)
GraduationDate = Annotated[
    date,
    Field(ge=date(1900, 1, 1), le=date(2100, 12, 31)),
]


class EnrollmentBeltApiPayload(BaseModel):
    belt_id: UUID
    graduated_on: GraduationDate


class BeltRecordApiRead(BaseModel):
    id: UUID
    graduated_on: date
    belt: BeltApiRead

    @classmethod
    def from_internal(cls, record: BeltRecord) -> 'BeltRecordApiRead':
        return cls(
            id=record.public_id,
            graduated_on=record.graduated_on,
            belt=BeltApiRead.from_internal(record.belt),
        )


class EnrollmentBeltsApiRead(BaseModel):
    current: BeltRecordApiRead | None
    eligibility: Eligibility
    eligible_on: date | None
    history: list[BeltRecordApiRead]


class PendingBeltEnrollmentApiRead(BaseModel):
    enrollment_id: UUID
    student_id: UUID
    student_name: str

    @classmethod
    def from_internal(
        cls, pending: PendingBeltEnrollment
    ) -> 'PendingBeltEnrollmentApiRead':
        return cls(
            enrollment_id=pending.enrollment_public_id,
            student_id=pending.student_public_id,
            student_name=pending.student_name,
        )


MAX_BULK_ITEMS = 200


class BulkBeltItemApi(BaseModel):
    enrollment_id: UUID
    belt_id: UUID
    graduated_on: GraduationDate


class BulkBeltRequest(BaseModel):
    items: list[BulkBeltItemApi] = Field(
        min_length=1, max_length=MAX_BULK_ITEMS
    )


class BulkBeltResultApiRead(BaseModel):
    saved: int
