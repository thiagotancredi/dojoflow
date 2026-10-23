import uuid
from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.rate_limit import public_pay_limiter
from dojoflow.models.academy import Academy
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.shared.enums import AcademyStatus
from tests.helpers.auth import SEED, auth_headers, other_academy_headers
from tests.helpers.scenario import add_modality, add_responsible, add_student

SETTINGS_URL = '/api/v1/academy/billing-settings'
PIX_SETTINGS = {
    'pix_key': 'dojo@exemplo.com',
    'pix_key_type': 'email',
    'pix_city': 'Goiânia',
    'recipient_name': 'Dojo Pix',
}


@pytest.fixture(autouse=True)
def _fresh_limiter() -> None:
    public_pay_limiter.reset()


def _freeze_today(monkeypatch: pytest.MonkeyPatch, today: date) -> None:
    monkeypatch.setattr(billing_module, 'local_today', lambda: today)


def _pay_url(token: str) -> str:
    return f'/api/v1/public/pay/{token}'


async def _token(session: AsyncSession, student_id: str) -> str:
    return await session.scalar(
        select(Student.pay_token).where(
            Student.public_id == uuid.UUID(student_id)
        )
    )


async def _overdue_student(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    *,
    birth_date: str = '1990-05-01',
    pix_settings: bool = True,
) -> dict:
    """Jan e fev/2027 de R$ 100 (dia 15); hoje 20/02: os dois atrasados."""
    headers = await auth_headers(client)
    if pix_settings:
        saved = await client.put(
            SETTINGS_URL, headers=headers, json=PIX_SETTINGS
        )
        assert saved.status_code == HTTPStatus.OK, saved.text
    modality_id = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        modality_id,
        name='Ana Lima',
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
        phone='62999990001',
        birth_date=birth_date,
    )
    _freeze_today(monkeypatch, date(2027, 2, 20))
    return {
        'headers': headers,
        'student_id': student_id,
        'token': await _token(db_session, student_id),
    }


@pytest.mark.asyncio
async def test_public_pay_open(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)

    response = await client.get(_pay_url(ctx['token']))

    assert response.status_code == HTTPStatus.OK, response.text
    body = response.json()
    assert body['academy_name'] == SEED.academy_name
    assert body['master_name'] == SEED.master_name
    assert body['greeting_name'] == 'Ana'
    assert body['status'] == 'open'
    assert body['items'] == [
        {'label': 'Mensalidade · janeiro', 'amount': '100.00'},
        {'label': 'Mensalidade · fevereiro', 'amount': '100.00'},
    ]
    assert body['total'] == '200.00'
    assert body['recipient_name'] == 'Dojo Pix'
    assert body['pix_code'].startswith('000201')
    assert '0116dojo@exemplo.com' in body['pix_code']
    assert '5406200.00' in body['pix_code']
    assert '6007GOIANIA' in body['pix_code']
    # Nada de telefone, chave crua ou outros dados
    assert set(body) == {
        'academy_name',
        'master_name',
        'greeting_name',
        'status',
        'items',
        'total',
        'recipient_name',
        'pix_code',
    }


@pytest.mark.asyncio
async def test_public_pay_minor_greets_responsible(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(
        client, db_session, monkeypatch, birth_date='2015-03-10'
    )
    await add_responsible(db_session, ctx['student_id'], 'Maria Lima')

    body = (await client.get(_pay_url(ctx['token']))).json()

    assert body['greeting_name'] == 'Maria'
    assert body['items'][0]['label'] == 'Mensalidade de Ana · janeiro'


@pytest.mark.asyncio
async def test_public_pay_clear_after_paying(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    # Abrir a ficha gera as mensalidades do aluno
    await client.get(
        f'/api/v1/students/{ctx["student_id"]}/billing',
        headers=ctx['headers'],
    )
    paid = await client.post(
        f'/api/v1/students/{ctx["student_id"]}/billing/payments',
        headers=ctx['headers'],
        json={'amount': '200', 'paid_on': '2027-02-20', 'method': 'pix'},
    )
    assert paid.status_code == HTTPStatus.CREATED, paid.text

    body = (await client.get(_pay_url(ctx['token']))).json()

    assert body['status'] == 'clear'
    assert body['items'] == []
    assert body['total'] == '0.00'
    assert body['pix_code'] is None


@pytest.mark.asyncio
async def test_public_pay_without_pix_settings_has_no_code(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(
        client, db_session, monkeypatch, pix_settings=False
    )

    body = (await client.get(_pay_url(ctx['token']))).json()

    assert body['status'] == 'open'
    assert body['pix_code'] is None
    assert body['recipient_name'] == SEED.academy_name


@pytest.mark.asyncio
async def test_public_pay_without_city_has_no_code(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    await client.put(
        SETTINGS_URL,
        headers=ctx['headers'],
        json={**PIX_SETTINGS, 'pix_city': ''},
    )

    body = (await client.get(_pay_url(ctx['token']))).json()

    assert body['pix_code'] is None


@pytest.mark.asyncio
async def test_public_pay_unknown_token_404(client: AsyncClient):
    response = await client.get(_pay_url('nao-existe'))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'PAY_LINK_INVALID'


@pytest.mark.asyncio
async def test_public_pay_blocked_academy_404(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    await db_session.execute(
        update(Academy)
        .where(Academy.id == SEED.academy_id)
        .values(status=AcademyStatus.BLOCKED)
    )
    await db_session.commit()

    response = await client.get(_pay_url(ctx['token']))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'PAY_LINK_INVALID'


@pytest.mark.asyncio
async def test_public_pay_rate_limited(client: AsyncClient):
    for _ in range(30):
        await client.get(_pay_url('x'))

    response = await client.get(_pay_url('x'))

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_renew_pay_link_invalidates_old(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    old = ctx['token']

    response = await client.post(
        f'/api/v1/students/{ctx["student_id"]}/billing/pay-link',
        headers=ctx['headers'],
    )

    assert response.status_code == HTTPStatus.OK, response.text
    new_token = response.json()['pay_url'].rsplit('/', 1)[1]
    assert new_token != old
    old_page = await client.get(_pay_url(old))
    assert old_page.status_code == HTTPStatus.NOT_FOUND
    new_page = await client.get(_pay_url(new_token))
    assert new_page.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_renew_pay_link_other_academy_404(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    other_headers = await other_academy_headers(db_session)

    response = await client.post(
        f'/api/v1/students/{ctx["student_id"]}/billing/pay-link',
        headers=other_headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert await _token(db_session, ctx['student_id']) == ctx['token']
