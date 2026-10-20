from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints, field_validator

from dojoflow.schemas.belt import BeltRead
from dojoflow.schemas.enrollment_belt import BeltRecord
from dojoflow.shared.enums import Eligibility

ListName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]


class GraduationListCreate(BaseModel):
    name: ListName
    modality_id: int
    exam_date: date


class GraduationListUpdate(BaseModel):
    name: ListName | None = None
    exam_date: date | None = None

    @field_validator('name', 'exam_date', mode='before')
    @classmethod
    def _reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError('This field cannot be null.')

        return value


class GraduationListSummary(BaseModel):
    id: int
    public_id: UUID
    name: str
    modality_id: int
    modality_public_id: UUID
    modality_name: str
    modality_emoji: str
    exam_date: date
    created_at: datetime
    entry_count: int


class GraduationCandidate(BaseModel):
    enrollment_id: int
    enrollment_public_id: UUID
    student_name: str
    current: BeltRecord | None
    eligibility: Eligibility
    suggested_target: BeltRead | None


class GraduationEntry(BaseModel):
    """Aluno na lista; faixa e data vêm do retrato guardado ao entrar."""

    id: int
    public_id: UUID
    enrollment_id: int
    enrollment_public_id: UUID
    student_name: str
    snapshot_belt: BeltRead | None
    snapshot_graduated_on: date | None
    eligibility: Eligibility
    target_belt: BeltRead


class GraduationListDetail(BaseModel):
    summary: GraduationListSummary
    belts: list[BeltRead]
    entries: list[GraduationEntry]
    candidates: list[GraduationCandidate]
