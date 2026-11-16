"""Cobranças avulsas (categorias), link com valor e token da graduação."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.models.payment import Payment
from dojoflow.models.student import Student
from dojoflow.shared.enums import ChargeCategory, PaymentKind
from tests.helpers.auth import SEED
from tests.helpers.scenario import add_modality, add_student, db_id

MONTH = date(2026, 11, 1)


def _charge(enrollment_id: int, kind: PaymentKind, **extra) -> Payment:
    return Payment(
        academy_id=SEED.academy_id,
        enrollment_id=enrollment_id,
        kind=kind,
        reference_month=MONTH,
        due_date=date(2026, 11, 16),
        amount_due=Decimal('150.00'),
        amount_paid=Decimal('0.00'),
        **extra,
    )


async def _enrollment(session: AsyncSession) -> int:
    modality = await add_modality(session, 'Karatê')
    _, enrollment = await add_student(session, modality)
    return await db_id(session, Enrollment, enrollment)


@pytest.mark.asyncio
async def test_two_extra_charges_same_month_allowed(db_session: AsyncSession):
    enrollment_id = await _enrollment(db_session)
    for _ in range(2):
        db_session.add(
            _charge(
                enrollment_id,
                PaymentKind.EXTRA,
                category=ChargeCategory.UNIFORM,
            )
        )
    await db_session.commit()


@pytest.mark.asyncio
async def test_two_monthly_same_month_still_unique(db_session: AsyncSession):
    enrollment_id = await _enrollment(db_session)
    db_session.add(_charge(enrollment_id, PaymentKind.MONTHLY))
    await db_session.commit()
    db_session.add(_charge(enrollment_id, PaymentKind.MONTHLY))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_new_student_link_month_is_current_month(
    db_session: AsyncSession,
):
    modality = await add_modality(db_session, 'Karatê')
    student, _ = await add_student(db_session, modality)
    row = await db_session.get(
        Student, await db_id(db_session, Student, student)
    )
    await db_session.refresh(row)
    assert row.pay_link_month == date.today().replace(day=1)
    assert row.pay_amount is None
    assert row.graduation_pay_token
    assert row.graduation_pay_token != row.pay_token
