from datetime import date, datetime
from decimal import Decimal
from typing import Literal
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


# Kids (até 12), Juvenil (13–17), Adulto (18–39), Master (40+) e sem data
AgeGroup = Literal['kids', 'juvenile', 'adult', 'master', 'unknown']


class AgeGroupCountRead(BaseModel):
    group: AgeGroup
    count: int


class ModalityAgeGroupsRead(BaseModel):
    modality_id: UUID
    modality_name: str
    groups: list[AgeGroupCountRead]


class AgeGroupsRead(BaseModel):
    # Alunos ativos; um aluno em duas modalidades conta uma vez em "all"
    all: list[AgeGroupCountRead]
    by_modality: list[ModalityAgeGroupsRead]


class BirthdayRead(BaseModel):
    student_id: UUID
    name: str
    day: int
    turning_age: int
    is_today: bool


class MonthCountRead(BaseModel):
    month: date  # primeiro dia do mês
    count: int


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
    # Soma do que está em atraso (todos os inadimplentes)
    overdue_total: Decimal
    age_groups: AgeGroupsRead
    # Aniversariantes do mês atual (alunos ativos), por dia
    birthdays: list[BirthdayRead]
    # Alunos novos (mês da primeira matrícula), últimos 6 meses
    new_students_by_month: list[MonthCountRead]
