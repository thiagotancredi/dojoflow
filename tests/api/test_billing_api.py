from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.models.payment import Payment
from dojoflow.services import billing as billing_module
from dojoflow.services.billing import BillingService
from tests.helpers.auth import auth_headers, other_academy_headers
from tests.helpers.scenario import add_modality, add_student


def _freeze_today(monkeypatch: pytest.MonkeyPatch, today: date) -> None:
    monkeypatch.setattr(billing_module, 'local_today', lambda: today)


def _url(student_id: str) -> str:
    return f'/api/v1/students/{student_id}/billing'


async def _read(
    client: AsyncClient, student_id: str, headers: dict[str, str]
) -> dict:
    response = await client.get(_url(student_id), headers=headers)
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()


@pytest.mark.asyncio
async def test_generation_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, enrollment_id = await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
    )
    _freeze_today(monkeypatch, date(2027, 3, 2))

    await _read(client, student_id, headers)
    body = await _read(client, student_id, headers)

    # Mais nova em cima: março, fevereiro, janeiro
    assert [c['reference_month'] for c in body['charges']] == [
        '2027-03-01',
        '2027-02-01',
        '2027-01-01',
    ]
    march = body['charges'][0]
    assert march['kind'] == 'monthly'
    assert march['enrollment_id'] == enrollment_id
    assert march['modality_name'] == 'Taekwondo'
    assert march['due_date'] == '2027-03-15'
    assert march['amount'] == '100.00'
    assert march['paid'] == '0.00'
    assert march['status'] == 'upcoming'
    assert body['charges'][1]['status'] == 'overdue'
    assert body['open_total'] == '300.00'
    assert body['open_months'] == 'janeiro, fevereiro e março'
    assert body['whatsapp_url'] is None
    assert body['payments'] == []

    total = await db_session.scalar(select(func.count()).select_from(Payment))
    assert total == 3  # noqa: PLR2004


@pytest.mark.asyncio
async def test_first_monthly_charge_is_next_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Matrícula em 20/10/2026, vencimento dia 10: a cobrança começa em
    # novembro (a taxa de matrícula entra na Tarefa 6)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        monthly_fee='120',
        due_day=10,
        billing_start_month='2026-11-01',
    )

    _freeze_today(monkeypatch, date(2026, 10, 20))
    body = await _read(client, student_id, headers)
    assert body['charges'] == []
    assert body['open_total'] == '0.00'
    assert not body['open_months']

    _freeze_today(monkeypatch, date(2026, 11, 1))
    body = await _read(client, student_id, headers)
    assert len(body['charges']) == 1
    november = body['charges'][0]
    assert november['reference_month'] == '2026-11-01'
    assert november['due_date'] == '2026-11-10'
    assert november['amount'] == '120.00'
    assert november['status'] == 'upcoming'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'kwargs',
    [
        {'status': 'inactive', 'monthly_fee': '100', 'due_day': 15},
        {'is_exempt': True, 'monthly_fee': '100', 'due_day': 15},
        {'monthly_fee': None, 'due_day': 15},
        {'monthly_fee': '100', 'due_day': None},
    ],
    ids=['inactive', 'exempt', 'no-fee', 'no-due-day'],
)
async def test_inactive_or_exempt_enrollment_generates_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict,
):
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        billing_start_month='2027-01-01',
        **kwargs,
    )
    _freeze_today(monkeypatch, date(2027, 3, 2))

    body = await _read(client, student_id, headers)

    assert body['charges'] == []


@pytest.mark.asyncio
async def test_billing_is_scoped_to_academy(
    client: AsyncClient, db_session: AsyncSession
):
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
    )
    other_headers = await other_academy_headers(db_session)

    response = await client.get(_url(student_id), headers=other_headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'STUDENT_NOT_FOUND'


@pytest.mark.asyncio
async def test_job_generates_for_every_academy(db_session: AsyncSession):
    taekwondo = await add_modality(db_session, 'Taekwondo')
    other = Academy(name='Outra Academia')
    db_session.add(other)
    await db_session.commit()
    await add_modality(db_session, 'Judô', academy_id=other.id)
    await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-03-01',
    )
    await add_student(
        db_session,
        taekwondo,
        name='Bruno Dias',
        monthly_fee='90',
        due_day=5,
        billing_start_month='2027-03-01',
        academy_id=other.id,
    )
    service = BillingService(db_session=db_session)

    created = await service.ensure_monthly_charges(None, date(2027, 3, 1))
    again = await service.ensure_monthly_charges(None, date(2027, 3, 1))

    assert created == 2  # noqa: PLR2004
    assert again == 0
