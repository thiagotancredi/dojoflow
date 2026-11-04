from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.email_log import EmailLog
from dojoflow.models.student import Student
from dojoflow.shared.enums import EmailKind
from tests.helpers.auth import SEED

MONTH = date(2026, 11, 1)


async def _student(session: AsyncSession) -> int:
    student = Student(academy_id=SEED.academy_id, name='Ana Lima')
    session.add(student)
    await session.flush()
    return student.id


def _log(kind: EmailKind, student_id: int) -> EmailLog:
    return EmailLog(
        kind=kind,
        academy_id=SEED.academy_id,
        student_id=student_id,
        recipient='ana@example.com',
        reference_month=MONTH,
    )


@pytest.mark.asyncio
async def test_billing_log_unique_per_student_and_month(
    db_session: AsyncSession,
) -> None:
    student_id = await _student(db_session)
    db_session.add(_log(EmailKind.BILLING, student_id))
    await db_session.flush()

    db_session.add(_log(EmailKind.BILLING, student_id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_password_reset_log_can_repeat(
    db_session: AsyncSession,
) -> None:
    student_id = await _student(db_session)
    db_session.add(_log(EmailKind.PASSWORD_RESET, student_id))
    db_session.add(_log(EmailKind.PASSWORD_RESET, student_id))

    await db_session.flush()
