"""Cadastro incompleto: alunos ativos sem para quem mandar a cobrança, sem
data de nascimento ou menores sem responsável."""

from datetime import date
from typing import Literal

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import (
    ADULT_AGE,
    BillingService,
    StudentContact,
    choose_email_recipient,
    choose_recipient,
)
from dojoflow.services.billing_rules import age_on
from dojoflow.shared.enums import EnrollmentStatus

IncompleteKind = Literal[
    'no_phone', 'no_birth_date', 'no_email', 'minor_without_responsible'
]
INCOMPLETE_KINDS: tuple[IncompleteKind, ...] = (
    'no_phone',
    'no_birth_date',
    'no_email',
    'minor_without_responsible',
)


def is_incomplete(
    contact: StudentContact, kind: IncompleteKind, today: date
) -> bool:
    if kind == 'no_phone':
        return choose_recipient(contact, today) is None
    if kind == 'no_email':
        return choose_email_recipient(contact, today) is None
    if kind == 'no_birth_date':
        return contact.birth_date is None
    return (
        contact.birth_date is not None
        and age_on(contact.birth_date, today) < ADULT_AGE
        and not contact.responsibles
    )


async def _active_contacts(
    db_session: AsyncSession, academy_id: int
) -> dict[int, StudentContact]:
    student_ids = set(
        (
            await db_session.scalars(
                select(distinct(Enrollment.student_id)).where(
                    Enrollment.academy_id == academy_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
        ).all()
    )
    return await BillingService(db_session).contacts(academy_id, student_ids)


async def incomplete_student_ids(
    db_session: AsyncSession,
    academy_id: int,
    kind: IncompleteKind,
    today: date | None = None,
) -> set[int]:
    today = today or local_today()
    contacts = await _active_contacts(db_session, academy_id)
    return {
        student_id
        for student_id, contact in contacts.items()
        if is_incomplete(contact, kind, today)
    }


async def incomplete_counts(
    db_session: AsyncSession, academy_id: int, today: date
) -> dict[IncompleteKind, int]:
    contacts = await _active_contacts(db_session, academy_id)
    return {
        kind: sum(
            1
            for contact in contacts.values()
            if is_incomplete(contact, kind, today)
        )
        for kind in INCOMPLETE_KINDS
    }
