from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.belt import Belt
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.graduation_list import GraduationList, GraduationListEntry
from dojoflow.models.payment import Payment
from dojoflow.shared.enums import PaymentKind
from tests.helpers.auth import SEED
from tests.helpers.scenario import (
    add_belt,
    add_graduation_list,
    add_modality,
    add_student,
    db_id,
)

MONTH = date(2026, 12, 1)


async def _setup(session: AsyncSession) -> tuple[int, int, int]:
    """(enrollment_id, list_id, belt_id) de um aluno de Taekwondo."""
    modality = await add_modality(session, 'Taekwondo')
    belt = await add_belt(session, modality, 'Verde')
    _, enrollment_id = await add_student(session, modality)
    listing = await add_graduation_list(session, modality, '2026-12-14')
    return (
        await db_id(session, Enrollment, enrollment_id),
        await db_id(session, GraduationList, listing['id']),
        await db_id(session, Belt, belt['id']),
    )


async def _entry(
    session: AsyncSession, enrollment_id: int, list_id: int, belt_id: int
) -> int:
    entry = GraduationListEntry(
        academy_id=SEED.academy_id,
        graduation_list_id=list_id,
        enrollment_id=enrollment_id,
        target_belt_id=belt_id,
    )
    session.add(entry)
    await session.flush()
    return entry.id


def _charge(
    enrollment_id: int, kind: PaymentKind, entry_id: int | None = None
) -> Payment:
    return Payment(
        academy_id=SEED.academy_id,
        enrollment_id=enrollment_id,
        kind=kind,
        reference_month=MONTH,
        due_date=date(2026, 12, 5),
        amount_due=Decimal('100.00'),
        amount_paid=Decimal('0.00'),
        graduation_entry_id=entry_id,
        description='Verde' if entry_id else None,
    )


@pytest.mark.asyncio
async def test_two_graduation_charges_same_month_are_allowed(
    db_session: AsyncSession,
) -> None:
    enrollment_id, list_id, belt_id = await _setup(db_session)
    other_list = GraduationList(
        academy_id=SEED.academy_id,
        modality_id=(
            await db_session.scalar(
                select(GraduationList.modality_id).where(
                    GraduationList.id == list_id
                )
            )
        ),
        name='Extra',
        exam_date=date(2026, 12, 20),
    )
    db_session.add(other_list)
    await db_session.flush()
    first = await _entry(db_session, enrollment_id, list_id, belt_id)
    second = await _entry(db_session, enrollment_id, other_list.id, belt_id)

    db_session.add(_charge(enrollment_id, PaymentKind.GRADUATION, first))
    db_session.add(_charge(enrollment_id, PaymentKind.GRADUATION, second))
    await db_session.flush()


@pytest.mark.asyncio
async def test_monthly_charge_stays_unique_per_month(
    db_session: AsyncSession,
) -> None:
    enrollment_id, _, _ = await _setup(db_session)
    db_session.add(_charge(enrollment_id, PaymentKind.MONTHLY))
    await db_session.flush()

    db_session.add(_charge(enrollment_id, PaymentKind.MONTHLY))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_removing_entry_keeps_paid_charge(
    db_session: AsyncSession,
) -> None:
    enrollment_id, list_id, belt_id = await _setup(db_session)
    entry_id = await _entry(db_session, enrollment_id, list_id, belt_id)
    charge = _charge(enrollment_id, PaymentKind.GRADUATION, entry_id)
    charge.amount_paid = Decimal('100.00')
    db_session.add(charge)
    await db_session.flush()

    await db_session.execute(
        delete(GraduationListEntry).where(GraduationListEntry.id == entry_id)
    )
    await db_session.refresh(charge)

    assert charge.graduation_entry_id is None
    assert charge.description == 'Verde'


@pytest.mark.asyncio
async def test_belt_price_defaults_to_zero(db_session: AsyncSession) -> None:
    _, _, belt_id = await _setup(db_session)

    price = await db_session.scalar(
        select(Belt.price).where(Belt.id == belt_id)
    )

    assert price == Decimal('0.00')
