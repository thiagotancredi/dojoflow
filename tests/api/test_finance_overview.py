"""Financeiro, aba Mensalidade: falta receber, quem não pagou, como pagaram,
por modalidade, quem deve há mais tempo e a contagem dos filtros."""

from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.services import billing as billing_module
from tests.helpers.auth import auth_headers
from tests.helpers.scenario import add_modality, add_student, generate_charges

URL = '/api/v1/billing/overview'
TODAY = date(2027, 3, 20)


async def _scenario(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Hoje 20/03/2027. Ana (R$ 100, dia 10, desde janeiro) pagou janeiro
    e deve fevereiro e março; Bruno (R$ 150, dia 25, desde março) pagou
    março no Pix; Caio é isento."""
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    ana, _ = await add_student(
        db_session,
        taekwondo,
        'Ana Lima',
        monthly_fee='100',
        due_day=10,
        billing_start_month='2027-01-01',
    )
    bruno, _ = await add_student(
        db_session,
        taekwondo,
        'Bruno Costa',
        monthly_fee='150',
        due_day=25,
        billing_start_month='2027-03-01',
    )
    await add_student(db_session, taekwondo, 'Caio Souza', is_exempt=True)
    await generate_charges(db_session, TODAY)

    for student, amount, paid_on in (
        (ana, '100', '2027-01-12'),
        (bruno, '150', '2027-03-15'),
    ):
        response = await client.post(
            f'/api/v1/students/{student}/billing/payments',
            headers=headers,
            json={'amount': amount, 'paid_on': paid_on, 'method': 'pix'},
        )
        assert response.status_code == HTTPStatus.CREATED, response.text

    return {'headers': headers, 'ana': ana, 'bruno': bruno}


async def _overview(client: AsyncClient, headers: dict, **params) -> dict:
    response = await client.get(URL, headers=headers, params=params)
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()


@pytest.mark.asyncio
async def test_open_total_includes_earlier_overdue(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    body = await _overview(client, ctx['headers'], month='2027-03')

    assert body['month_open_total'] == '200.00'
    assert body['unpaid_students'] == 1


@pytest.mark.asyncio
async def test_past_month_ignores_later_charges(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    body = await _overview(client, ctx['headers'], month='2027-02')

    # Só fevereiro da Ana; março (depois do mês escolhido) fica de fora
    assert body['month_open_total'] == '100.00'
    assert body['unpaid_students'] == 1


@pytest.mark.asyncio
async def test_by_method_and_modality(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    body = await _overview(client, ctx['headers'], month='2027-03')

    assert body['by_method'] == [{'method': 'pix', 'amount': '150.00'}]
    assert body['by_modality'] == [
        {
            'modality_name': 'Taekwondo',
            'expected': '250.00',
            'received': '150.00',
        }
    ]


@pytest.mark.asyncio
async def test_filter_counts_and_default_filter(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    default = await _overview(client, ctx['headers'], month='2027-03')
    upcoming = await _overview(
        client, ctx['headers'], month='2027-03', filter='upcoming'
    )

    assert default['items'] == upcoming['items'] == []
    assert default['filter_counts'] == {
        'overdue': 1,
        'upcoming': 0,
        'paid': 1,
        'all': 2,
    }


@pytest.mark.asyncio
async def test_item_due_date(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    body = await _overview(
        client, ctx['headers'], month='2027-03', filter='overdue'
    )

    (item,) = body['items']
    assert item['name'] == 'Ana Lima'
    assert item['due_date'] == '2027-02-10'


@pytest.mark.asyncio
async def test_longest_overdue_lists_five(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    for day in range(1, 7):
        await add_student(
            db_session,
            taekwondo,
            f'Aluno {day}',
            monthly_fee='100',
            due_day=day,
            billing_start_month='2027-02-01',
        )
    await generate_charges(db_session, TODAY)

    body = await _overview(client, headers, month='2027-03')

    assert [s['name'] for s in body['longest_overdue']] == [
        'Aluno 1',
        'Aluno 2',
        'Aluno 3',
        'Aluno 4',
        'Aluno 5',
    ]
    assert body['longest_overdue'][0]['days_late'] == 47  # noqa: PLR2004
    assert body['overdue_students'] == 6  # noqa: PLR2004
