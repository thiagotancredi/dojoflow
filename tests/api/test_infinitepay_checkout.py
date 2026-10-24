import uuid
from datetime import date, timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.rate_limit import public_pay_limiter
from dojoflow.core.settings import settings
from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.shared.enums import CheckoutStatus
from tests.helpers.auth import SEED, auth_headers
from tests.helpers.infinitepay import (
    API_KEY,
    checkout_disabled,
    enable_infinitepay,
    fake_infinitepay,
    key_rejected,
    link_created,
)
from tests.helpers.scenario import (
    add_modality,
    add_responsible,
    add_student,
    generate_charges,
)

TODAY = date(2027, 2, 20)
LINK = 'https://checkout.infinitepay.io/katsuflow/abc'


@pytest.fixture(autouse=True)
def _fresh_limiter() -> None:
    public_pay_limiter.reset()


async def _student(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    *,
    phone: str | None = '62999990001',
    birth_date: str = '1990-05-01',
) -> dict:
    """Jan e fev/2027 de R$ 100 (dia 15); hoje 20/02: os dois atrasados."""
    modality_id = await add_modality(session, 'Taekwondo')
    student_id, _ = await add_student(
        session,
        modality_id,
        name='Ana Lima',
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
        phone=phone,
        birth_date=birth_date,
    )
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    await generate_charges(session, TODAY)
    token = await session.scalar(
        select(Student.pay_token).where(
            Student.public_id == uuid.UUID(student_id)
        )
    )
    return {'student_id': student_id, 'token': token}


def _checkout_url(token: str) -> str:
    return f'/api/v1/public/pay/{token}/checkout'


async def _checkouts(session: AsyncSession) -> list[InfinitePayCheckout]:
    session.expire_all()
    return list(
        (
            await session.scalars(
                select(InfinitePayCheckout).order_by(InfinitePayCheckout.id)
            )
        ).all()
    )


@pytest.mark.asyncio
async def test_public_pay_checkout_enabled_hides_pix_code(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await client.put(
        '/api/v1/academy/billing-settings',
        headers=await auth_headers(client),
        json={
            'pix_key': 'dojo@exemplo.com',
            'pix_key_type': 'email',
            'pix_city': 'Goiânia',
        },
    )
    before = (await client.get(f'/api/v1/public/pay/{ctx["token"]}')).json()
    await enable_infinitepay(db_session)

    after = (await client.get(f'/api/v1/public/pay/{ctx["token"]}')).json()

    assert before['checkout_enabled'] is False
    assert before['pix_code'] is not None
    assert after['checkout_enabled'] is True
    assert after['pix_code'] is None
    assert after['total'] == '200.00'


@pytest.mark.asyncio
async def test_checkout_creates_link_with_overdue_total(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)

    with fake_infinitepay(link_created(LINK)) as fake:
        response = await client.post(_checkout_url(ctx['token']))

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json() == {'url': LINK}
    [request] = fake.requests
    assert request.headers['X-Api-Key'] == API_KEY
    [body] = fake.bodies('/links')
    assert body['items'] == [
        {
            'description': 'Mensalidade · janeiro',
            'quantity': 1,
            'price': 10000,
        },
        {
            'description': 'Mensalidade · fevereiro',
            'quantity': 1,
            'price': 10000,
        },
    ]
    assert body['customer'] == {
        'name': 'Ana Lima',
        'phone_number': '+5562999990001',
    }
    assert body['redirect_url'] == (
        f'{settings.WEB_APP_URL}/pagar/{ctx["token"]}'
    )
    assert body['webhook_url'] == (
        f'{settings.WEB_APP_URL}{settings.API_V1_PREFIX}'
        '/public/webhooks/infinitepay'
    )
    # Número do pedido aleatório e longo
    assert len(body['order_nsu']) >= 32  # noqa: PLR2004

    [checkout] = await _checkouts(db_session)
    assert checkout.order_nsu == body['order_nsu']
    assert checkout.academy_id == SEED.academy_id
    assert checkout.amount == Decimal('200.00')
    assert checkout.url == LINK
    assert checkout.handle == 'katsuflow'
    assert checkout.status is CheckoutStatus.OPEN


@pytest.mark.asyncio
async def test_checkout_order_numbers_are_unique(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)
    with fake_infinitepay():
        await client.post(_checkout_url(ctx['token']))
    await db_session.execute(update(InfinitePayCheckout).values(amount=1))
    await db_session.commit()

    with fake_infinitepay():
        await client.post(_checkout_url(ctx['token']))

    first, second = await _checkouts(db_session)
    assert first.order_nsu != second.order_nsu


@pytest.mark.asyncio
async def test_checkout_reuses_open_link_same_amount(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)
    with fake_infinitepay(link_created(LINK)):
        await client.post(_checkout_url(ctx['token']))

    with fake_infinitepay(link_created('https://outro')) as fake:
        response = await client.post(_checkout_url(ctx['token']))

    assert response.json() == {'url': LINK}
    assert fake.requests == []
    assert len(await _checkouts(db_session)) == 1


@pytest.mark.asyncio
async def test_checkout_new_link_when_old_one_expired(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)
    with fake_infinitepay(link_created(LINK)):
        await client.post(_checkout_url(ctx['token']))
    await db_session.execute(
        update(InfinitePayCheckout).values(
            created_at=func.now() - timedelta(hours=25)
        )
    )
    await db_session.commit()

    with fake_infinitepay(link_created('https://novo')) as fake:
        response = await client.post(_checkout_url(ctx['token']))

    assert response.json() == {'url': 'https://novo'}
    assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_checkout_new_link_when_amount_changed(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)
    with fake_infinitepay(link_created(LINK)):
        await client.post(_checkout_url(ctx['token']))
    # Março venceu: o total em aberto passa a R$ 300
    march = date(2027, 3, 20)
    monkeypatch.setattr(billing_module, 'local_today', lambda: march)
    await generate_charges(db_session, march)

    with fake_infinitepay(link_created('https://novo')) as fake:
        response = await client.post(_checkout_url(ctx['token']))

    assert response.json() == {'url': 'https://novo'}
    assert len(fake.bodies('/links')[0]['items']) == 3  # noqa: PLR2004
    amounts = [c.amount for c in await _checkouts(db_session)]
    assert amounts == [Decimal('200.00'), Decimal('300.00')]


@pytest.mark.asyncio
async def test_checkout_minor_uses_responsible_as_customer(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch, birth_date='2015-03-10')
    await add_responsible(db_session, ctx['student_id'], 'Maria Lima')
    await enable_infinitepay(db_session)

    with fake_infinitepay() as fake:
        await client.post(_checkout_url(ctx['token']))

    [body] = fake.bodies('/links')
    assert body['customer'] == {
        'name': 'Maria Lima',
        'phone_number': '+5562988880001',
    }
    assert body['items'][0]['description'] == ('Mensalidade de Ana · janeiro')


@pytest.mark.asyncio
async def test_checkout_sends_email_when_known(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await db_session.execute(update(Student).values(email='ana@exemplo.com'))
    await db_session.commit()
    await enable_infinitepay(db_session)

    with fake_infinitepay() as fake:
        await client.post(_checkout_url(ctx['token']))

    assert fake.bodies('/links')[0]['customer']['email'] == 'ana@exemplo.com'


@pytest.mark.asyncio
async def test_checkout_without_phone_sends_name_only(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch, phone=None)
    await enable_infinitepay(db_session)

    with fake_infinitepay() as fake:
        await client.post(_checkout_url(ctx['token']))

    assert fake.bodies('/links')[0]['customer'] == {'name': 'Ana Lima'}


@pytest.mark.asyncio
async def test_checkout_disabled_409(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session, enabled=False)

    with fake_infinitepay() as fake:
        response = await client.post(_checkout_url(ctx['token']))

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'INFINITEPAY_DISABLED'
    assert fake.requests == []


@pytest.mark.asyncio
async def test_checkout_nothing_overdue_409(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)
    # Antes do vencimento de janeiro: nada vencido
    monkeypatch.setattr(
        billing_module, 'local_today', lambda: date(2027, 1, 2)
    )

    with fake_infinitepay() as fake:
        response = await client.post(_checkout_url(ctx['token']))

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'NOTHING_TO_PAY'
    assert fake.requests == []


@pytest.mark.asyncio
async def test_checkout_unavailable_409(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)

    with fake_infinitepay(key_rejected()):
        response = await client.post(_checkout_url(ctx['token']))

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'INFINITEPAY_UNAVAILABLE'
    assert API_KEY not in response.text
    assert await _checkouts(db_session) == []


@pytest.mark.asyncio
async def test_checkout_unknown_token_404(client: AsyncClient):
    with fake_infinitepay() as fake:
        response = await client.post(_checkout_url('nao-existe'))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'PAY_LINK_INVALID'
    assert fake.requests == []


@pytest.mark.asyncio
async def test_checkout_sends_handle(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)

    with fake_infinitepay() as fake:
        await client.post(_checkout_url(ctx['token']))

    assert fake.bodies('/links')[0]['handle'] == 'katsuflow'


@pytest.mark.parametrize('failure', [key_rejected, checkout_disabled])
@pytest.mark.asyncio
async def test_checkout_refused_turns_integration_off(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    failure,
):
    # Chave apagada ou checkout desligado na InfinitePay: a página volta ao
    # Pix copia e cola em vez de deixar o aluno sem como pagar
    ctx = await _student(db_session, monkeypatch)
    await client.put(
        '/api/v1/academy/billing-settings',
        headers=await auth_headers(client),
        json={
            'pix_key': 'dojo@exemplo.com',
            'pix_key_type': 'email',
            'pix_city': 'Goiânia',
        },
    )
    await enable_infinitepay(db_session)

    with fake_infinitepay(failure()):
        response = await client.post(_checkout_url(ctx['token']))

    assert response.status_code == HTTPStatus.CONFLICT
    page = (await client.get(f'/api/v1/public/pay/{ctx["token"]}')).json()
    assert page['checkout_enabled'] is False
    assert page['pix_code'] is not None
    status = await client.get(
        '/api/v1/academy/infinitepay', headers=await auth_headers(client)
    )
    assert status.json()['enabled'] is False


@pytest.mark.asyncio
async def test_checkout_network_failure_keeps_integration_on(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    from tests.helpers.infinitepay import unreachable  # noqa: PLC0415

    ctx = await _student(db_session, monkeypatch)
    await enable_infinitepay(db_session)

    with fake_infinitepay(unreachable()):
        await client.post(_checkout_url(ctx['token']))

    page = (await client.get(f'/api/v1/public/pay/{ctx["token"]}')).json()
    assert page['checkout_enabled'] is True
