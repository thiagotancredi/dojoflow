from datetime import date, datetime
from decimal import Decimal
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


class OverdueStudentRead(BaseModel):
    student_id: UUID
    name: str
    modality: str
    amount: Decimal
    days_late: int


class DueSoonChargeRead(BaseModel):
    student_id: UUID
    name: str
    modality: str
    amount: Decimal
    due_date: date


class DashboardSummaryRead(BaseModel):
    active_students: int
    students_by_modality: list[ModalityCountRead]
    recent_enrollments: list[RecentEnrollmentRead]
    registration_pending: list[PendingEnrollmentRead]
    overdue: list[OverdueStudentRead]
    due_soon: list[DueSoonChargeRead]
    # Totais (as listas acima param em 5)
    overdue_students: int
    due_soon_students: int
