from datetime import date
from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.belt_api import BeltApiRead
from dojoflow.schemas.enrollment_belt import BeltRecord
from dojoflow.shared.enums import Eligibility


class EnrollmentBeltApiPayload(BaseModel):
    belt_id: UUID
    graduated_on: date


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
