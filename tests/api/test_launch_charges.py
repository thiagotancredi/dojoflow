"""Lançar cobrança (mês atual, categorias) e adiantamento de mensalidade."""

from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.models.payment import Payment
from dojoflow.services import billing as billing_module
from dojoflow.shared.enums import PaymentKind
from tests.helpers.auth import auth_headers
from tests.helpers.scenario import (
    add_modality,
    add_student,
    db_id,
    generate_charges,
)

TODAY = date(2026, 11, 16)


async def _student(  # noqa: PLR0913
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    *,
    start: str = '2026-11-01',
    status: str = 'active',
    is_exempt: bool = False,
) -> dict:
    """R$ 100 com vencimento no dia 10; hoje 16/11/2026."""
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    modality = await add_modality(session, 'Karatê')
    student_id, enrollment_id = await add_student(
        session,
        modality,
        status=status,
        monthly_fee='100',
        due_day=10,
        billing_start_month=start,
        is_exempt=is_exempt,
    )
    await generate_charges(session, TODAY)
    return {
        'headers': await auth_headers(client),
        'url': f'/api/v1/students/{student_id}/billing',
        'enrollment_id': enrollment_id,
    }


async def _launch(client: AsyncClient, ctx: dict, **payload):
    return await client.post(
        f'{ctx["url"]}/charges',
        headers=ctx['headers'],
        json={'enrollment_id': ctx['enrollment_id'], **payload},
    )


async def _advance(client: AsyncClient, ctx: dict, months: int):
    return await client.post(
        f'{ctx["url"]}/charges/advance',
        headers=ctx['headers'],
        json={'enrollment_id': ctx['enrollment_id'], 'months': months},
    )


async def _monthly_months(session: AsyncSession, ctx: dict) -> list[str]:
    enrollment_id = await db_id(session, Enrollment, ctx['enrollment_id'])
    rows = await session.scalars(
        select(Payment.reference_month)
        .where(
            Payment.enrollment_id == enrollment_id,
            Payment.kind == PaymentKind.MONTHLY,
        )
        .order_by(Payment.reference_month)
    )
    return [month.isoformat() for month in rows]


@pytest.mark.asyncio
async def test_launch_current_month_after_reactivation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Reativado em novembro: a cobrança automática só começa em dezembro
    ctx = await _student(client, db_session, monkeypatch, start='2026-12-01')

    response = await _launch(
        client,
        ctx,
        kind='monthly',
        reference_month='2026-11-01',
        amount='100',
        due_date='2026-11-16',
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    assert response.json()['reference_month'] == '2026-11-01'


@pytest.mark.asyncio
async def test_launch_future_month_conflicts(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _launch(
        client,
        ctx,
        kind='monthly',
        reference_month='2026-12-01',
        amount='100',
        due_date='2026-12-10',
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'CHARGE_MONTH_IN_FUTURE'


@pytest.mark.asyncio
async def test_launch_extra_uniform(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _launch(
        client,
        ctx,
        kind='extra',
        category='uniform',
        amount='150',
        due_date='2026-11-16',
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    charge = response.json()
    assert charge['kind'] == 'extra'
    assert charge['category'] == 'uniform'
    assert charge['reference_month'] == '2026-11-01'
    assert charge['amount'] == '150.00'


@pytest.mark.asyncio
async def test_launch_two_extras_same_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch)
    for _ in range(2):
        response = await _launch(
            client,
            ctx,
            kind='extra',
            category='uniform',
            amount='150',
            due_date='2026-11-16',
        )
        assert response.status_code == HTTPStatus.CREATED, response.text


@pytest.mark.asyncio
async def test_launch_other_requires_description(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _launch(
        client,
        ctx,
        kind='extra',
        category='other',
        description='  ',
        amount='30',
        due_date='2026-11-16',
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_launch_category_without_extra_is_422(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _launch(
        client,
        ctx,
        kind='enrollment_fee',
        category='uniform',
        amount='80',
        due_date='2026-11-16',
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_advance_three_months_after_last(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _advance(client, ctx, 3)

    assert response.status_code == HTTPStatus.CREATED, response.text
    charges = response.json()
    assert [c['reference_month'] for c in charges] == [
        '2026-12-01',
        '2027-01-01',
        '2027-02-01',
    ]
    assert [c['due_date'] for c in charges] == [
        '2026-12-10',
        '2027-01-10',
        '2027-02-10',
    ]
    assert {c['amount'] for c in charges} == {'100.00'}


@pytest.mark.asyncio
async def test_advance_starts_at_current_month_when_missing(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch, start='2026-12-01')

    response = await _advance(client, ctx, 3)

    assert response.status_code == HTTPStatus.CREATED, response.text
    assert [c['reference_month'] for c in response.json()] == [
        '2026-11-01',
        '2026-12-01',
        '2027-01-01',
    ]


@pytest.mark.asyncio
async def test_generation_after_advance_no_gap_no_duplicate(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(client, db_session, monkeypatch, start='2026-12-01')
    assert (await _advance(client, ctx, 3)).status_code == HTTPStatus.CREATED

    await generate_charges(db_session, date(2026, 12, 1))
    await generate_charges(db_session, date(2027, 2, 1))

    assert await _monthly_months(db_session, ctx) == [
        '2026-11-01',
        '2026-12-01',
        '2027-01-01',
        '2027-02-01',
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'student', [{'status': 'inactive'}, {'is_exempt': True}]
)
async def test_advance_refused_for_exempt_or_inactive(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    student: dict,
):
    ctx = await _student(client, db_session, monkeypatch, **student)

    response = await _advance(client, ctx, 2)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'ADVANCE_NOT_AVAILABLE'


@pytest.mark.asyncio
@pytest.mark.parametrize('months', [0, 13])
async def test_advance_months_out_of_range_is_422(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    months: int,
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _advance(client, ctx, months)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
