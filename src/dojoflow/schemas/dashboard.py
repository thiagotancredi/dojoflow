from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.billing import BeltLookApiRead
from dojoflow.shared.enums import StudentSex


class ModalityCountRead(BaseModel):
    modality_id: UUID
    modality_name: str
    count: int


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


class BeltCountRead(BeltLookApiRead):
    id: UUID
    count: int


class ModalityBeltsRead(BaseModel):
    """Matrículas ativas pela faixa atual, na ordem das faixas."""

    modality_id: UUID
    modality_name: str
    belts: list[BeltCountRead]
    without_belt: int


class SexCountRead(BaseModel):
    sex: StudentSex | None  # None = não informado
    count: int


class IncompleteCountsRead(BaseModel):
    """Alunos ativos com o cadastro incompleto, por motivo."""

    no_phone: int
    no_birth_date: int
    no_email: int
    minor_without_responsible: int


class DashboardSummaryRead(BaseModel):
    active_students: int
    students_by_modality: list[ModalityCountRead]
    age_groups: AgeGroupsRead
    # Aniversariantes do mês atual (alunos ativos), por dia
    birthdays: list[BirthdayRead]
    # Alunos novos (mês da primeira matrícula), últimos 12 meses
    new_students_by_month: list[MonthCountRead]
    by_belt: list[ModalityBeltsRead]
    by_sex: list[SexCountRead]
    incomplete: IncompleteCountsRead
