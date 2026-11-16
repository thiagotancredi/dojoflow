"""Virada do mês: quem ainda está com o link do mês anterior ganha um novo,
do total em aberto (uma vez por mês)."""

import uuid
from datetime import date
from decimal import Decimal
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.rate_limit import public_pay_limiter
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.services.billing import BillingService
from tests.helpers.scenario import add_modality, add_student, generate_charges


@pytest.fixture(autouse=True)
def _fresh_limiter() -> None:
    public_pay_limiter.reset()


async def _student_with_value_link(
    session: AsyncSession, link_month: date
) -> str:
    """Aluno com um link de R$ 50 gerado no mês `link_month`."""
    modality = await add_modality(session, 'Karatê')
    student_id, _ = await add_student(
        session,
        modality,
        monthly_fee='100',
        due_day=10,
        billing_start_month='2026-10-01',
    )
    await session.execute(
        update(Student)
        .where(Student.public_id == uuid.UUID(student_id))
        .values(pay_amount=Decimal('50.00'), pay_link_month=link_month)
    )
    await session.commit()
    return student_id


async def _row(session: AsyncSession, student_id: str) -> Student:
    session.expire_all()
    return await session.scalar(
        select(Student).where(Student.public_id == uuid.UUID(student_id))
    )


@pytest.mark.asyncio
async def test_reset_on_first_day_rotates_old_links(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    today = date(2026, 11, 1)
    monkeypatch.setattr(billing_module, 'local_today', lambda: today)
    student_id = await _student_with_value_link(db_session, date(2026, 10, 1))
    old = (await _row(db_session, student_id)).pay_token

    # O worker do dia 1º troca os links antes de gerar as mensalidades
    await generate_charges(db_session, today)
    changed = await BillingService(db_session).reset_pay_links(today)
    await db_session.commit()

    row = await _row(db_session, student_id)
    assert changed == 0  # o job já trocou; de novo no mesmo dia, nada
    assert row.pay_token != old
    assert row.pay_amount is None
    assert row.pay_link_month == today
    page = await client.get(f'/api/v1/public/pay/{row.pay_token}')
    assert page.status_code == HTTPStatus.OK
    assert page.json()['total'] == '200.00'
    gone = await client.get(f'/api/v1/public/pay/{old}')
    assert gone.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_reset_runs_once_per_month(db_session: AsyncSession):
    today = date(2026, 11, 1)
    student_id = await _student_with_value_link(db_session, date(2026, 10, 1))
    service = BillingService(db_session)
    await service.reset_pay_links(today)
    await db_session.commit()
    token = (await _row(db_session, student_id)).pay_token

    again = await service.reset_pay_links(today)
    await db_session.commit()

    assert again == 0
    assert (await _row(db_session, student_id)).pay_token == token


@pytest.mark.asyncio
async def test_reset_mid_month_keeps_links(db_session: AsyncSession):
    student_id = await _student_with_value_link(db_session, date(2026, 11, 1))
    before = await _row(db_session, student_id)
    token, amount = before.pay_token, before.pay_amount

    changed = await BillingService(db_session).reset_pay_links(
        date(2026, 11, 16)
    )
    await db_session.commit()

    after = await _row(db_session, student_id)
    assert changed == 0
    assert (after.pay_token, after.pay_amount) == (token, amount)


@pytest.mark.asyncio
async def test_reset_keeps_graduation_token(db_session: AsyncSession):
    student_id = await _student_with_value_link(db_session, date(2026, 10, 1))
    graduation = (await _row(db_session, student_id)).graduation_pay_token

    await BillingService(db_session).reset_pay_links(date(2026, 11, 1))
    await db_session.commit()

    assert (await _row(db_session, student_id)).graduation_pay_token == (
        graduation
    )
