"""Link com valor: o mestre digita quanto cobrar, um link por aluno, e a
graduação com o link próprio."""

import uuid
from datetime import date
from decimal import Decimal
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.rate_limit import public_pay_limiter
from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.models.payment import Payment
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.services.infinitepay import InfinitePayService
from dojoflow.shared.enums import CheckoutStatus, PaymentKind
from tests.helpers.auth import SEED, auth_headers
from tests.helpers.infinitepay import (
    FakeInfinitePay,
    enable_infinitepay,
    payment_paid,
)
from tests.helpers.scenario import add_modality, add_student, generate_charges

TODAY = date(2026, 11, 16)
ORDER = 'order-value-link'


@pytest.fixture(autouse=True)
def _fresh_limiter() -> None:
    public_pay_limiter.reset()


async def _student(
    client: AsyncClient, session: AsyncSession, monkeypatch
) -> dict:
    """Outubro e novembro atrasados (R$ 100, dia 10) e um uniforme de
    R$ 150 vencendo hoje: R$ 350 em aberto."""
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    modality = await add_modality(session, 'Karatê')
    student_id, enrollment_id = await add_student(
        session,
        modality,
        monthly_fee='100',
        due_day=10,
        billing_start_month='2026-10-01',
        phone='62999990001',
    )
    await generate_charges(session, TODAY)
    ctx = {
        'headers': await auth_headers(client),
        'url': f'/api/v1/students/{student_id}/billing',
        'student_id': student_id,
        'enrollment_id': enrollment_id,
    }
    await _launch_extra(client, ctx, 'uniform', '150')
    return ctx


async def _launch_extra(client, ctx, category: str, amount: str) -> None:
    response = await client.post(
        f'{ctx["url"]}/charges',
        headers=ctx['headers'],
        json={
            'enrollment_id': ctx['enrollment_id'],
            'kind': 'extra',
            'category': category,
            'amount': amount,
            'due_date': TODAY.isoformat(),
        },
    )
    assert response.status_code == HTTPStatus.CREATED, response.text


async def _pay_link(client, ctx, amount: str):
    return await client.post(
        f'{ctx["url"]}/pay-link',
        headers=ctx['headers'],
        json={'amount': amount},
    )


def _token(url: str) -> str:
    return urlparse(url).path.split('/')[2]


async def _page(client: AsyncClient, token: str, suffix: str = ''):
    return await client.get(f'/api/v1/public/pay/{token}{suffix}')


async def _student_row(session: AsyncSession, ctx: dict) -> Student:
    session.expire_all()
    return await session.scalar(
        select(Student).where(
            Student.public_id == uuid.UUID(ctx['student_id'])
        )
    )


async def _manual_payment(client, ctx, amount: str) -> None:
    response = await client.post(
        f'{ctx["url"]}/payments',
        headers=ctx['headers'],
        json={'amount': amount, 'paid_on': TODAY.isoformat(), 'method': 'pix'},
    )
    assert response.status_code == HTTPStatus.CREATED, response.text


@pytest.mark.asyncio
async def test_pay_link_value_page_shows_allocation(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _pay_link(client, ctx, '250')

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['amount'] == '250.00'
    body = (await _page(client, _token(response.json()['pay_url']))).json()
    assert body['items'] == [
        {'label': 'Mensalidade · outubro', 'amount': '100.00'},
        {'label': 'Mensalidade · novembro', 'amount': '100.00'},
        {'label': 'Uniforme · parte', 'amount': '50.00'},
    ]
    assert body['total'] == '250.00'


@pytest.mark.asyncio
async def test_pay_link_cancels_previous_link(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)
    old = (await _student_row(db_session, ctx)).pay_token

    response = await _pay_link(client, ctx, '100')

    new = _token(response.json()['pay_url'])
    assert new != old
    assert (await _page(client, old)).status_code == HTTPStatus.NOT_FOUND
    assert (await _page(client, new)).status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_pay_link_above_open_total_conflicts(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _pay_link(client, ctx, '500')

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'PAY_LINK_EXCEEDS_OPEN'
    assert 'R$ 350,00' in response.json()['detail']


@pytest.mark.asyncio
async def test_pay_link_zero_is_422(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _pay_link(client, ctx, '0')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_pay_link_whatsapp_uses_link_value(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)

    response = await _pay_link(client, ctx, '250')

    text = parse_qs(urlparse(response.json()['whatsapp_url']).query)['text'][0]
    assert 'R$ 250,00' in text
    assert response.json()['pay_url'] in text


@pytest.mark.asyncio
async def test_manual_payment_after_value_link_caps_page(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)
    token = _token((await _pay_link(client, ctx, '250')).json()['pay_url'])

    await _manual_payment(client, ctx, '300')

    body = (await _page(client, token)).json()
    assert body['total'] == '50.00'
    await _manual_payment(client, ctx, '50')
    assert (await _page(client, token)).json()['status'] == 'clear'


async def _open_checkout(
    session: AsyncSession, ctx: dict, amount: str
) -> None:
    student = await _student_row(session, ctx)
    session.add(
        InfinitePayCheckout(
            academy_id=SEED.academy_id,
            student_id=student.id,
            handle='katsuflow',
            order_nsu=ORDER,
            amount=Decimal(amount),
            url='https://checkout.infinitepay.io/katsuflow/x',
        )
    )
    await session.commit()


async def _settle(session: AsyncSession, cents: int) -> CheckoutStatus | None:
    fake = FakeInfinitePay(payment_paid(cents))
    return await InfinitePayService(session, fake.client()).settle(
        ORDER, 'tx-1', 'slug-1'
    )


@pytest.mark.asyncio
async def test_settle_value_link_after_new_charge(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)
    await enable_infinitepay(db_session)
    await _pay_link(client, ctx, '200')
    await _open_checkout(db_session, ctx, '200')
    await _launch_extra(client, ctx, 'event', '80')

    status = await _settle(db_session, 20000)

    assert status is CheckoutStatus.PAID
    db_session.expire_all()
    paid = (
        await db_session.execute(
            select(Payment.kind, Payment.amount_paid).order_by(
                Payment.due_date, Payment.id
            )
        )
    ).all()
    assert [(kind, str(value)) for kind, value in paid] == [
        (PaymentKind.MONTHLY, '100.00'),
        (PaymentKind.MONTHLY, '100.00'),
        (PaymentKind.EXTRA, '0.00'),
        (PaymentKind.EXTRA, '0.00'),
    ]


@pytest.mark.asyncio
async def test_settle_amount_above_owed_goes_to_review(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)
    await enable_infinitepay(db_session)
    await _open_checkout(db_session, ctx, '400')

    status = await _settle(db_session, 40000)

    assert status is CheckoutStatus.REVIEW


@pytest.mark.asyncio
async def test_graduation_link_survives_monthly_pay_link(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    ctx = await _student(client, db_session, monkeypatch)
    student = await _student_row(db_session, ctx)
    graduation_token = student.graduation_pay_token

    await _pay_link(client, ctx, '100')

    response = await _page(client, graduation_token, '?group=graduation')
    assert response.status_code == HTTPStatus.OK
    assert (await _student_row(db_session, ctx)).graduation_pay_token == (
        graduation_token
    )
