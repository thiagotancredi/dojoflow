import asyncio
import uuid
from datetime import date
from decimal import Decimal
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from dojoflow.api.dependencies.rate_limit import public_pay_limiter
from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.models.payment_transaction import PaymentTransaction
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.services.infinitepay import InfinitePayService
from dojoflow.shared.enums import CheckoutStatus, PaymentMethod
from dojoflow.worker import tasks
from tests.conftest import TEST_DATABASE_URL
from tests.helpers.auth import SEED, auth_headers
from tests.helpers.infinitepay import (
    FakeInfinitePay,
    enable_infinitepay,
    payment_not_found,
    payment_paid,
    unreachable,
)
from tests.helpers.scenario import add_modality, add_student, generate_charges

TODAY = date(2027, 2, 20)
ORDER = 'order-abc-123'
TX = 'tx-fc3c0858'
SLUG = 'b6JwL3ZmAt'
RECEIPT = 'https://recibo.infinitepay.io/abc'


@pytest.fixture(autouse=True)
def _fresh_limiter() -> None:
    public_pay_limiter.reset()


async def _scenario(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> dict:
    """Ana deve jan e fev (R$ 200) e tem um link aberto de R$ 200."""
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    modality_id = await add_modality(session, 'Taekwondo')
    student_public_id, _ = await add_student(
        session,
        modality_id,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
        phone='62999990001',
    )
    await generate_charges(session, TODAY)
    await enable_infinitepay(session)
    student = await session.scalar(
        select(Student).where(
            Student.public_id == uuid.UUID(student_public_id)
        )
    )
    session.add(
        InfinitePayCheckout(
            academy_id=SEED.academy_id,
            student_id=student.id,
            handle='katsuflow',
            order_nsu=ORDER,
            amount=Decimal('200.00'),
            url='https://checkout.infinitepay.io/katsuflow/x',
        )
    )
    await session.commit()
    return {
        'student_id': student.id,
        'student_public_id': student_public_id,
        'token': student.pay_token,
    }


async def _settle(session: AsyncSession, fake: FakeInfinitePay, **kwargs):
    params = {
        'order_nsu': ORDER,
        'transaction_nsu': TX,
        'slug': SLUG,
        'receipt_url': RECEIPT,
    }
    params.update(kwargs)
    return await InfinitePayService(session, fake.client()).settle(
        params.pop('order_nsu'),
        params.pop('transaction_nsu'),
        params.pop('slug'),
        **params,
    )


async def _checkout(session: AsyncSession) -> InfinitePayCheckout:
    session.expire_all()
    return await session.scalar(
        select(InfinitePayCheckout).where(
            InfinitePayCheckout.order_nsu == ORDER
        )
    )


async def _transactions(session: AsyncSession) -> list[PaymentTransaction]:
    session.expire_all()
    return list((await session.scalars(select(PaymentTransaction))).all())


async def _open_total(client: AsyncClient, student_public_id: str) -> str:
    response = await client.get(
        f'/api/v1/students/{student_public_id}/billing',
        headers=await auth_headers(client),
    )
    return response.json()['open_total']


# --- Rotas: só enfileiram -------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_enqueues_settlement(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    calls: list[dict] = []
    monkeypatch.setattr(
        tasks.settle_infinitepay_payment,
        'delay',
        lambda *args, **kwargs: calls.append({'args': args, **kwargs}),
    )

    response = await client.post(
        '/api/v1/public/webhooks/infinitepay',
        json={
            'order_nsu': ORDER,
            'transaction_nsu': TX,
            'invoice_slug': SLUG,
            'amount': 20000,
            'paid_amount': 20000,
            'capture_method': 'pix',
            'installments': 1,
            'receipt_url': RECEIPT,
            'items': [{'description': 'x', 'quantity': 1, 'price': 20000}],
        },
    )

    assert response.status_code == HTTPStatus.OK, response.text
    assert calls == [
        {
            'args': (),
            'order_nsu': ORDER,
            'transaction_nsu': TX,
            'slug': SLUG,
            'receipt_url': RECEIPT,
        }
    ]


@pytest.mark.asyncio
async def test_webhook_missing_fields_422(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    calls: list = []
    monkeypatch.setattr(
        tasks.settle_infinitepay_payment, 'delay', lambda **k: calls.append(k)
    )

    response = await client.post(
        '/api/v1/public/webhooks/infinitepay',
        json={'amount': 20000, 'invoice_slug': SLUG},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert calls == []


@pytest.mark.asyncio
async def test_confirm_enqueues_with_student_id(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(db_session, monkeypatch)
    calls: list[dict] = []
    monkeypatch.setattr(
        tasks.settle_infinitepay_payment, 'delay', lambda **k: calls.append(k)
    )

    response = await client.post(
        f'/api/v1/public/pay/{ctx["token"]}/confirm',
        json={
            'order_nsu': ORDER,
            'transaction_nsu': TX,
            'slug': SLUG,
            'receipt_url': RECEIPT,
        },
    )

    assert response.status_code == HTTPStatus.ACCEPTED, response.text
    assert response.json() == {'status': 'processing'}
    assert calls == [
        {
            'order_nsu': ORDER,
            'transaction_nsu': TX,
            'slug': SLUG,
            'receipt_url': RECEIPT,
            'student_id': ctx['student_id'],
        }
    ]


@pytest.mark.asyncio
async def test_confirm_unknown_token_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    calls: list = []
    monkeypatch.setattr(
        tasks.settle_infinitepay_payment, 'delay', lambda **k: calls.append(k)
    )

    response = await client.post(
        '/api/v1/public/pay/nao-existe/confirm',
        json={'order_nsu': ORDER, 'transaction_nsu': TX, 'slug': SLUG},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert calls == []


# --- Regra: o núcleo do worker -------------------------------------------


@pytest.mark.asyncio
async def test_settle_paid_creates_automatic_payment(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(db_session, monkeypatch)
    fake = FakeInfinitePay(payment_paid(20000, 'pix'))

    status = await _settle(db_session, fake)

    assert status is CheckoutStatus.PAID
    # Conferido com a tag guardada no link
    [check] = fake.bodies('/payment_check')
    assert check == {
        'handle': 'katsuflow',
        'order_nsu': ORDER,
        'transaction_nsu': TX,
        'slug': SLUG,
    }
    [transaction] = await _transactions(db_session)
    assert transaction.source.value == 'infinitepay'
    assert transaction.payment_method is PaymentMethod.PIX
    assert transaction.gross_amount == Decimal('200.00')
    assert transaction.received_at == TODAY
    assert transaction.notes == 'InfinitePay'
    transaction_id = transaction.id
    checkout = await _checkout(db_session)
    assert checkout.status is CheckoutStatus.PAID
    assert checkout.transaction_nsu == TX
    assert checkout.invoice_slug == SLUG
    assert checkout.receipt_url == RECEIPT
    assert checkout.capture_method == 'pix'
    assert checkout.paid_amount == Decimal('200.00')
    assert checkout.paid_at is not None
    assert checkout.payment_transaction_id == transaction_id
    assert await _open_total(client, ctx['student_public_id']) == '0.00'


@pytest.mark.asyncio
async def test_settle_card_method_credit_card(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    await _scenario(db_session, monkeypatch)
    # Cartão com taxa repassada: o aluno paga mais que o link
    fake = FakeInfinitePay(payment_paid(20000, 'credit_card', 21000))

    await _settle(db_session, fake)

    [transaction] = await _transactions(db_session)
    assert transaction.payment_method is PaymentMethod.CREDIT_CARD
    assert transaction.gross_amount == Decimal('200.00')


@pytest.mark.asyncio
async def test_settle_unknown_method_is_other(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    await _scenario(db_session, monkeypatch)

    await _settle(db_session, FakeInfinitePay(payment_paid(20000, 'boleto')))

    [transaction] = await _transactions(db_session)
    assert transaction.payment_method is PaymentMethod.OTHER


@pytest.mark.asyncio
async def test_settle_twice_same_transaction_creates_one_payment(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    await _scenario(db_session, monkeypatch)
    fake = FakeInfinitePay(payment_paid())

    first = await _settle(db_session, fake)
    again = await _settle(db_session, fake)

    assert first is CheckoutStatus.PAID
    assert again is CheckoutStatus.PAID
    assert len(await _transactions(db_session)) == 1


@pytest.mark.asyncio
async def test_settle_at_the_same_time_creates_one_payment(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    # Aviso e volta do aluno chegando juntos, em duas conexões
    await _scenario(db_session, monkeypatch)
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def settle_in_own_session() -> CheckoutStatus | None:
        async with sessions() as session:
            return await _settle(session, FakeInfinitePay(payment_paid()))

    try:
        results = await asyncio.gather(
            settle_in_own_session(), settle_in_own_session()
        )
    finally:
        await engine.dispose()

    assert results == [CheckoutStatus.PAID, CheckoutStatus.PAID]
    assert len(await _transactions(db_session)) == 1


@pytest.mark.asyncio
async def test_settle_not_paid_does_nothing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    await _scenario(db_session, monkeypatch)

    status = await _settle(db_session, FakeInfinitePay(payment_not_found()))

    assert status is None
    assert await _transactions(db_session) == []
    checkout = await _checkout(db_session)
    assert checkout.status is CheckoutStatus.OPEN
    assert checkout.transaction_nsu is None


@pytest.mark.asyncio
async def test_settle_paid_less_than_link_does_nothing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    await _scenario(db_session, monkeypatch)

    status = await _settle(
        db_session, FakeInfinitePay(payment_paid(20000, 'pix', 15000))
    )

    assert status is None
    assert await _transactions(db_session) == []


@pytest.mark.asyncio
async def test_settle_unknown_order_returns_none(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    await _scenario(db_session, monkeypatch)
    fake = FakeInfinitePay(payment_paid())

    status = await _settle(db_session, fake, order_nsu='inventado')

    assert status is None
    assert fake.requests == []
    assert await _transactions(db_session) == []


@pytest.mark.asyncio
async def test_settle_unavailable_raises(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    from dojoflow.integrations.infinitepay.client import (  # noqa: PLC0415
        InfinitePayUnavailable,
    )

    await _scenario(db_session, monkeypatch)

    with pytest.raises(InfinitePayUnavailable):
        await _settle(db_session, FakeInfinitePay(unreachable()))

    assert await _transactions(db_session) == []
    assert (await _checkout(db_session)).status is CheckoutStatus.OPEN


@pytest.mark.asyncio
async def test_manual_payment_cancels_open_checkout(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(db_session, monkeypatch)

    response = await client.post(
        f'/api/v1/students/{ctx["student_public_id"]}/billing/payments',
        headers=await auth_headers(client),
        json={'amount': '100.00', 'paid_on': '2027-02-20', 'method': 'cash'},
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    assert (await _checkout(db_session)).status is CheckoutStatus.CANCELED
    [transaction] = await _transactions(db_session)
    assert transaction.source.value == 'manual'


@pytest.mark.asyncio
async def test_paid_after_manual_payment_goes_to_review(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(db_session, monkeypatch)
    await client.post(
        f'/api/v1/students/{ctx["student_public_id"]}/billing/payments',
        headers=await auth_headers(client),
        json={'amount': '200.00', 'paid_on': '2027-02-20', 'method': 'cash'},
    )

    status = await _settle(db_session, FakeInfinitePay(payment_paid()))

    assert status is CheckoutStatus.REVIEW
    # Nada lançado sozinho: só a baixa manual
    assert len(await _transactions(db_session)) == 1
    checkout = await _checkout(db_session)
    assert checkout.status is CheckoutStatus.REVIEW
    assert checkout.transaction_nsu == TX
    assert checkout.receipt_url == RECEIPT
    assert checkout.payment_transaction_id is None


@pytest.mark.asyncio
async def test_canceled_link_goes_to_review_even_if_total_matches(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Baixa manual de R$ 100 e depois março vence: o total volta a R$ 200,
    # mas o link era de jan+fev — o mestre confere
    ctx = await _scenario(db_session, monkeypatch)
    await client.post(
        f'/api/v1/students/{ctx["student_public_id"]}/billing/payments',
        headers=await auth_headers(client),
        json={'amount': '100.00', 'paid_on': '2027-02-20', 'method': 'cash'},
    )
    march = date(2027, 3, 20)
    monkeypatch.setattr(billing_module, 'local_today', lambda: march)
    await generate_charges(db_session, march)

    status = await _settle(db_session, FakeInfinitePay(payment_paid()))

    assert status is CheckoutStatus.REVIEW
    assert len(await _transactions(db_session)) == 1


@pytest.mark.asyncio
async def test_paid_after_disconnect_still_settles(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await _scenario(db_session, monkeypatch)
    # Mestre desligou e trocou a tag; o link antigo usa a tag dele
    await enable_infinitepay(db_session, handle='outra-tag', enabled=False)
    fake = FakeInfinitePay(payment_paid())

    status = await _settle(db_session, fake)

    assert status is CheckoutStatus.PAID
    assert fake.bodies('/payment_check')[0]['handle'] == 'katsuflow'


@pytest.mark.asyncio
async def test_confirm_with_other_students_order_is_ignored(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    ctx = await _scenario(db_session, monkeypatch)
    fake = FakeInfinitePay(payment_paid())

    status = await _settle(
        db_session, fake, student_id=ctx['student_id'] + 999
    )

    assert status is None
    assert fake.requests == []
    assert await _transactions(db_session) == []


@pytest.mark.asyncio
async def test_settle_with_owner_student_id_settles(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    ctx = await _scenario(db_session, monkeypatch)

    status = await _settle(
        db_session,
        FakeInfinitePay(payment_paid()),
        student_id=ctx['student_id'],
    )

    assert status is CheckoutStatus.PAID


@pytest.mark.asyncio
async def test_undo_automatic_payment_reopens_charges(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(db_session, monkeypatch)
    await _settle(db_session, FakeInfinitePay(payment_paid()))
    [transaction] = await _transactions(db_session)

    response = await client.delete(
        f'/api/v1/students/{ctx["student_public_id"]}/billing/payments/'
        f'{transaction.public_id}',
        headers=await auth_headers(client),
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _open_total(client, ctx['student_public_id']) == '200.00'
    # O aviso repetido não lança de novo
    again = await _settle(db_session, FakeInfinitePay(payment_paid()))
    assert again is CheckoutStatus.PAID
    assert await _transactions(db_session) == []


@pytest.mark.asyncio
async def test_settle_counts_only_payments_of_that_student(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    await _scenario(db_session, monkeypatch)

    await _settle(db_session, FakeInfinitePay(payment_paid()))

    count = await db_session.scalar(
        select(func.count()).select_from(PaymentTransaction)
    )
    assert count == 1
