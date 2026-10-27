"""Monta cenários direto no banco, sem passar pela API.

Use só na preparação dos testes: cada endpoint usado aqui já tem testes
próprios pela API (modalidades, faixas, alunos, histórico, listas).
A ação que o teste quer verificar continua indo pela API.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.belt import Belt
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.graduation_list import GraduationList
from dojoflow.models.modality import Modality
from dojoflow.models.responsible import Responsible
from dojoflow.models.student import Student
from dojoflow.models.student_responsible import StudentResponsible
from dojoflow.shared.enums import (
    DurationUnit,
    EnrollmentStatus,
    StudentResponsibleRelationship,
)
from dojoflow.worker.tasks import generate_monthly_charges_job
from tests.helpers.auth import SEED


async def _one(session: AsyncSession, model: type, value: str) -> Any:
    return await session.scalar(
        select(model).where(model.public_id == uuid.UUID(value))
    )


async def add_modality(
    session: AsyncSession,
    name: str,
    academy_id: int | None = None,
) -> str:
    """Modalidade no catálogo, já oferecida pela academia."""
    modality = Modality(name=name, emoji='🥋', is_active=True)
    session.add(modality)
    await session.flush()
    session.add(
        AcademyModality(
            academy_id=academy_id or SEED.academy_id,
            modality_id=modality.id,
        )
    )
    await session.commit()

    return str(modality.public_id)


async def add_belt(  # noqa: PLR0913
    session: AsyncSession,
    modality_id: str,
    name: str,
    *,
    primary_color: str = '#f8fafc',
    min_time_amount: int | None = None,
    min_time_unit: str | None = None,
    academy_id: int | None = None,
) -> dict[str, str]:
    """Faixa no fim da sequência da modalidade."""
    academy_id = academy_id or SEED.academy_id
    modality = await _one(session, Modality, modality_id)
    last_position = await session.scalar(
        select(func.max(Belt.position)).where(
            Belt.academy_id == academy_id,
            Belt.modality_id == modality.id,
        )
    )
    belt = Belt(
        academy_id=academy_id,
        modality_id=modality.id,
        name=name,
        primary_color=primary_color,
        min_time_amount=min_time_amount,
        min_time_unit=DurationUnit(min_time_unit) if min_time_unit else None,
        position=(last_position or 0) + 1,
    )
    session.add(belt)
    await session.commit()

    return {'id': str(belt.public_id), 'name': name}


async def add_student(  # noqa: PLR0913
    session: AsyncSession,
    modality_id: str,
    name: str = 'Ana Lima',
    status: str = 'active',
    *,
    monthly_fee: str | None = None,
    due_day: int | None = None,
    billing_start_month: str | None = None,
    is_exempt: bool = False,
    academy_id: int | None = None,
    phone: str | None = None,
    birth_date: str | None = None,
) -> tuple[str, str]:
    """Aluno com matrícula; devolve (student_id, enrollment_id)."""
    academy_id = academy_id or SEED.academy_id
    modality = await _one(session, Modality, modality_id)
    student = Student(
        academy_id=academy_id,
        name=name,
        phone=phone,
        birth_date=date.fromisoformat(birth_date) if birth_date else None,
    )
    session.add(student)
    await session.flush()
    enrollment = Enrollment(
        academy_id=academy_id,
        student_id=student.id,
        modality_id=modality.id,
        status=EnrollmentStatus(status),
        monthly_fee=Decimal(monthly_fee) if monthly_fee else None,
        due_day=due_day,
        billing_start_month=(
            date.fromisoformat(billing_start_month)
            if billing_start_month
            else None
        ),
        is_exempt=is_exempt,
    )
    session.add(enrollment)
    await session.commit()

    return str(student.public_id), str(enrollment.public_id)


async def add_belt_record(
    session: AsyncSession,
    student: tuple[str, str],
    belt: dict[str, str],
    graduated_on: str,
) -> None:
    """Registro no histórico de faixas da matrícula."""
    enrollment = await _one(session, Enrollment, student[1])
    belt_row = await _one(session, Belt, belt['id'])
    session.add(
        EnrollmentBelt(
            academy_id=SEED.academy_id,
            enrollment_id=enrollment.id,
            belt_id=belt_row.id,
            graduated_on=date.fromisoformat(graduated_on),
        )
    )
    await session.commit()


async def add_graduation_list(
    session: AsyncSession,
    modality_id: str,
    exam_date: str,
    name: str = 'Novembro/2026',
) -> dict[str, str]:
    """Lista de graduação vazia."""
    modality = await _one(session, Modality, modality_id)
    graduation_list = GraduationList(
        academy_id=SEED.academy_id,
        modality_id=modality.id,
        name=name,
        exam_date=date.fromisoformat(exam_date),
    )
    session.add(graduation_list)
    await session.commit()

    return {'id': str(graduation_list.public_id)}


async def add_responsible(
    session: AsyncSession,
    student_id: str,
    name: str = 'Maria Lima',
    phone: str = '62988880001',
) -> None:
    """Responsável ligado ao aluno (mãe)."""
    student = await _one(session, Student, student_id)
    responsible = Responsible(
        academy_id=student.academy_id, name=name, phone=phone
    )
    session.add(responsible)
    await session.flush()
    session.add(
        StudentResponsible(
            academy_id=student.academy_id,
            student_id=student.id,
            responsible_id=responsible.id,
            relationship=StudentResponsibleRelationship.MOTHER,
        )
    )
    await session.commit()


async def generate_charges(session: AsyncSession, today: date) -> int:
    """Faz o papel do worker: cria as mensalidades que faltam até hoje."""
    return await generate_monthly_charges_job(session, today)
