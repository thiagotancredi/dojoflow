from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ModalityCountRead(BaseModel):
    modality_id: UUID
    modality_name: str
    count: int


class RecentEnrollmentRead(BaseModel):
    student_id: UUID
    student_name: str
    modality_name: str
    created_at: datetime


class PendingEnrollmentRead(BaseModel):
    enrollment_id: UUID
    student_id: UUID
    student_name: str
    modality_name: str


class DashboardSummaryRead(BaseModel):
    active_students: int
    students_by_modality: list[ModalityCountRead]
    recent_enrollments: list[RecentEnrollmentRead]
    registration_pending: list[PendingEnrollmentRead]
