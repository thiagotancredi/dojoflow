"""Baixa em lote: vários alunos que pagaram o que deviam, de uma vez."""

from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.models.payment_transaction import PaymentTransaction
from dojoflow.services import billing as billing_module
from tests.helpers.auth import auth_headers, other_academy_headers
from tests.helpers.scenario import add_modality, add_student

URL = '/api/v1/billing/bulk-payments'
TODAY = date(2027, 3, 2)


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)


async def _student(
    db_session: AsyncSession,
    modality: str,
    name: str,
    fee: str,
    academy_id: int | None = None,
) -> str:
    student_id, _ = await add_student(
        db_session,
        modality,
        name,
        monthly_fee=fee,
        due_day=10,
        billing_start_month='2027-02-01',
        academy_id=academy_id,
    )
    return student_id


async def _open_total(
    client: AsyncClient, headers: dict[str, str], student_id: str
) -> str:
    response = await client.get(
        f'/api/v1/students/{student_id}/billing', headers=headers
    )
    assert response.status_code == HTTPStatus.OK

    return response.json()['open_total']


async def _transactions(db_session: AsyncSession) -> int:
    return int(
        await db_session.scalar(select(func.count(PaymentTransaction.id))) or 0
    )


@pytest.mark.asyncio
async def test_bulk_payment_settles_each_selected_student(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    tkd = await add_modality(db_session, 'Taekwondo')
    ana = await _student(db_session, tkd, 'Ana', '100')
    bruno = await _student(db_session, tkd, 'Bruno', '150')
    # Fevereiro (atrasado) + março (a vencer) de cada um
    assert await _open_total(client, headers, ana) == '200.00'
    assert await _open_total(client, headers, bruno) == '300.00'

    response = await client.post(
        URL,
        headers=headers,
        json={
            'paid_on': '2027-03-02',
            'method': 'pix',
            'items': [
                {'student_id': ana, 'amount': '200.00'},
                {'student_id': bruno, 'amount': '300.00'},
            ],
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    assert response.json() == {'count': 2, 'total': '500.00'}
    assert await _open_total(client, headers, ana) == '0.00'
    assert await _open_total(client, headers, bruno) == '0.00'
    # Um pagamento por aluno
    assert await _transactions(db_session) == len(['ana', 'bruno'])


@pytest.mark.asyncio
async def test_bulk_payment_is_all_or_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    tkd = await add_modality(db_session, 'Taekwondo')
    ana = await _student(db_session, tkd, 'Ana', '100')
    bruno = await _student(db_session, tkd, 'Bruno', '150')

    response = await client.post(
        URL,
        headers=headers,
        json={
            'paid_on': '2027-03-02',
            'items': [
                {'student_id': ana, 'amount': '200.00'},
                # Mais do que Bruno deve: a baixa inteira é recusada
                {'student_id': bruno, 'amount': '999.00'},
            ],
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'PAYMENT_EXCEEDS_OPEN'
    assert await _transactions(db_session) == 0
    assert await _open_total(client, headers, ana) == '200.00'


@pytest.mark.asyncio
async def test_bulk_payment_rejects_student_of_another_academy(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    await other_academy_headers(db_session)
    other = await db_session.scalar(
        select(Academy).where(Academy.name == 'Outra Academia')
    )
    assert other is not None
    judo = await add_modality(db_session, 'Judô', academy_id=other.id)
    outsider = await _student(
        db_session, judo, 'De fora', '100', academy_id=other.id
    )

    response = await client.post(
        URL,
        headers=headers,
        json={
            'paid_on': '2027-03-02',
            'items': [{'student_id': outsider, 'amount': '100.00'}],
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'STUDENT_NOT_FOUND'
    assert await _transactions(db_session) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'items',
    [
        [],
        'duplicated',
        [
            {
                'student_id': '00000000-0000-0000-0000-000000000000',
                'amount': '0',
            }
        ],
    ],
)
async def test_bulk_payment_validates_items(
    client: AsyncClient,
    db_session: AsyncSession,
    items: object,
) -> None:
    headers = await auth_headers(client)
    if items == 'duplicated':
        tkd = await add_modality(db_session, 'Taekwondo')
        ana = await _student(db_session, tkd, 'Ana', '100')
        items = [
            {'student_id': ana, 'amount': '100.00'},
            {'student_id': ana, 'amount': '100.00'},
        ]

    response = await client.post(
        URL,
        headers=headers,
        json={'paid_on': '2027-03-02', 'items': items},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
