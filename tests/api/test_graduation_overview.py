"""Financeiro, aba Graduação: previsto, recebido, falta receber, quem não
pagou e a tabela de exames."""

from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.services import billing as billing_module
from tests.helpers.auth import auth_headers, other_academy_headers
from tests.helpers.scenario import (
    add_belt,
    add_graduation_list,
    add_modality,
    add_student,
)

URL = '/api/v1/billing/graduation-overview'
LISTS_URL = '/api/v1/graduation-lists'
TODAY = date(2026, 11, 20)


async def _entry(
    client: AsyncClient,
    headers: dict,
    list_id: str,
    enrollment_id: str,
    belt_id: str,
) -> None:
    response = await client.post(
        f'{LISTS_URL}/{list_id}/entries',
        headers=headers,
        json={'enrollment_id': enrollment_id, 'target_belt_id': belt_id},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.text


async def _pay(
    client: AsyncClient, headers: dict, student_id: str, amount: str
) -> None:
    response = await client.post(
        f'/api/v1/students/{student_id}/billing/payments',
        headers=headers,
        json={
            'amount': amount,
            'paid_on': '2026-11-15',
            'method': 'pix',
            'group': 'graduation',
        },
    )
    assert response.status_code == HTTPStatus.CREATED, response.text


async def _scenario(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Hoje 20/11/2026. Lista A (pagar até 28/11, Verde R$ 100): Ana pagou,
    Bruno deve. Lista B (pagar até 10/10, Azul R$ 120): Caio pagou R$ 40.
    Lista C sem data limite (não cobra)."""
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    verde = await add_belt(db_session, taekwondo, 'Verde', price='100')
    azul = await add_belt(db_session, taekwondo, 'Azul', price='120')
    students = {
        name: await add_student(db_session, taekwondo, name)
        for name in ('Ana Lima', 'Bruno Costa', 'Caio Souza')
    }
    lists = {
        'A': await add_graduation_list(
            db_session,
            taekwondo,
            '2026-11-30',
            name='Exame de novembro',
            payment_due_date='2026-11-28',
        ),
        'B': await add_graduation_list(
            db_session,
            taekwondo,
            '2026-10-12',
            name='Exame de outubro',
            payment_due_date='2026-10-10',
        ),
        'C': await add_graduation_list(
            db_session, taekwondo, '2026-12-14', name='Exame sem data'
        ),
    }
    for list_key, student, belt in (
        ('A', 'Ana Lima', verde),
        ('A', 'Bruno Costa', verde),
        ('B', 'Caio Souza', azul),
        ('C', 'Ana Lima', azul),
    ):
        await _entry(
            client,
            headers,
            lists[list_key]['id'],
            students[student][1],
            belt['id'],
        )
    await _pay(client, headers, students['Ana Lima'][0], '100')
    await _pay(client, headers, students['Caio Souza'][0], '40')

    return {'headers': headers, 'students': students, 'lists': lists}


async def _overview(client: AsyncClient, headers: dict, month: str) -> dict:
    response = await client.get(URL, headers=headers, params={'month': month})
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()


@pytest.mark.asyncio
async def test_expected_counts_only_deadline_in_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    body = await _overview(client, ctx['headers'], '2026-11')

    assert body['expected'] == '200.00'
    assert body['received'] == '140.00'


@pytest.mark.asyncio
async def test_partial_payment_counts_what_is_left(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    body = await _overview(client, ctx['headers'], '2026-11')

    # Bruno deve 100 (lista A) e Caio ainda deve 80 (lista B, atrasada)
    assert body['open_total'] == '180.00'
    assert body['unpaid_students'] == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_exams_include_old_list_with_debt(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    body = await _overview(client, ctx['headers'], '2026-11')

    old, current = body['exams']
    assert old['list_id'] == ctx['lists']['B']['id']
    assert old['name'] == 'Exame de outubro'
    assert old['modality_name'] == 'Taekwondo'
    assert old['total'] == '120.00'
    assert old['received'] == '40.00'
    assert old['owing'] == 1
    assert old['days_late'] == 41  # noqa: PLR2004
    assert old['days_to_due'] is None

    assert current['list_id'] == ctx['lists']['A']['id']
    assert current['exam_date'] == '2026-11-30'
    assert current['payment_due_date'] == '2026-11-28'
    assert current['total'] == '200.00'
    assert current['received'] == '100.00'
    assert current['owing'] == 1
    assert current['days_late'] is None
    assert current['days_to_due'] == 8  # noqa: PLR2004


@pytest.mark.asyncio
async def test_fully_paid_old_list_disappears(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    await _pay(client, ctx['headers'], ctx['students']['Caio Souza'][0], '80')

    body = await _overview(client, ctx['headers'], '2026-11')

    assert [e['list_id'] for e in body['exams']] == [ctx['lists']['A']['id']]


@pytest.mark.asyncio
async def test_graduation_overview_scoped_to_academy(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await _scenario(client, db_session, monkeypatch)
    response = await client.get(
        URL,
        headers=await other_academy_headers(db_session),
        params={'month': '2026-11'},
    )

    assert response.status_code == HTTPStatus.OK, response.text
    body = response.json()
    assert body['expected'] == body['open_total'] == '0.00'
    assert body['unpaid_students'] == 0
    assert body['exams'] == []
