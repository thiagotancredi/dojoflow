from decimal import Decimal

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import EnrollmentStatus


class EnrollmentCreate(BaseModel):
    academy_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    modality_id: int = Field(gt=0)
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=1, le=31)
    is_exempt: bool = False


class EnrollmentRead(ReadBase):
    academy_id: int
    student_id: int
    modality_id: int
    status: EnrollmentStatus
    monthly_fee: Decimal | None
    due_day: int | None
    is_exempt: bool
