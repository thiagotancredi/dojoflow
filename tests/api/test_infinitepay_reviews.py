import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.services.infinitepay import InfinitePayService
from dojoflow.shared.enums import CheckoutStatus
from tests.helpers.auth import SEED, auth_headers, other_academy_headers
from tests.helpers.infinitepay import (
    FakeInfinitePay,
    enable_infinitepay,
    payment_paid,
)
from tests.helpers.scenario import add_modality, add_student, generate_charges

TODAY = date(2027, 2, 20)
RECEIPT = 'https://recibo.infinitepay.io/abc'


async def _student(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> dict:
    """Ana deve jan e fev (R$ 200)."""
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    modality_id = await add_modality(session, 'Taekwondo')
    public_id, _ = await add_student(
        session,
        modality_id,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
    )
    await generate_charges(session, TODAY)
    await enable_infinitepay(session)
    student = await session.scalar(
        select(Student).where(Student.public_id == uuid.UUID(public_id))
    )
    return {'public_id': public_id, 'id': student.id}


async def _checkout(
    session: AsyncSession,
    student_id: int,
    status: CheckoutStatus,
    *,
    paid_amount: str = '200.00',
) -> InfinitePayCheckout:
    checkout = InfinitePayCheckout(
        academy_id=SEED.academy_id,
        student_id=student_id,
        handle='katsuflow',
        order_nsu=uuid.uuid4().hex,
        amount=Decimal('200.00'),
        url='https://checkout.infinitepay.io/x',
        status=status,
        transaction_nsu=uuid.uuid4().hex,
        receipt_url=RECEIPT,
        paid_amount=Decimal(paid_amount),
        # 01:30 UTC de 21/02 = 22:30 de 20/02 em Brasília
        paid_at=datetime(2027, 2, 21, 1, 30, tzinfo=UTC),
    )
    session.add(checkout)
    await session.commit()
    return checkout


async def _billing(client: AsyncClient, public_id: str, headers=None):
    response = await client.get(
        f'/api/v1/students/{public_id}/billing',
        headers=headers or await auth_headers(client),
    )
    return response


@pytest.mark.asyncio
async def test_student_billing_shows_automatic_source_and_receipt(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    db_session.add(
        InfinitePayCheckout(
            academy_id=SEED.academy_id,
            student_id=ctx['id'],
            handle='katsuflow',
            order_nsu='order-1',
            amount=Decimal('200.00'),
            url='https://checkout.infinitepay.io/x',
        )
    )
    await db_session.commit()
    await InfinitePayService(
        db_session, FakeInfinitePay(payment_paid()).client()
    ).settle('order-1', 'tx-1', 'slug', receipt_url=RECEIPT)

    body = (await _billing(client, ctx['public_id'])).json()

    automatic = [p for p in body['payments'] if p['source'] == 'infinitepay']
    assert len(automatic) == 1
    assert automatic[0]['receipt_url'] == RECEIPT
    assert automatic[0]['method'] == 'pix'
    assert automatic[0]['amount'] == '200.00'


@pytest.mark.asyncio
async def test_manual_payment_has_manual_source_and_no_receipt(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    headers = await auth_headers(client)
    created = await client.post(
        f'/api/v1/students/{ctx["public_id"]}/billing/payments',
        headers=headers,
        json={'amount': '100.00', 'paid_on': '2027-02-20', 'method': 'cash'},
    )

    assert created.json()['source'] == 'manual'
    assert created.json()['receipt_url'] is None
    [payment] = (await _billing(client, ctx['public_id'])).json()['payments']
    assert payment['source'] == 'manual'
    assert payment['receipt_url'] is None


@pytest.mark.asyncio
async def test_student_billing_lists_reviews(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    review = await _checkout(
        db_session, ctx['id'], CheckoutStatus.REVIEW, paid_amount='210.00'
    )
    await _checkout(db_session, ctx['id'], CheckoutStatus.RESOLVED)
    await _checkout(db_session, ctx['id'], CheckoutStatus.PAID)

    body = (await _billing(client, ctx['public_id'])).json()

    assert body['reviews'] == [
        {
            'id': str(review.public_id),
            'amount': '210.00',
            'paid_at': '2027-02-20',
            'receipt_url': RECEIPT,
        }
    ]


@pytest.mark.asyncio
async def test_resolve_review_hides_it(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    review = await _checkout(db_session, ctx['id'], CheckoutStatus.REVIEW)
    review_id = review.id
    headers = await auth_headers(client)

    response = await client.post(
        f'/api/v1/students/{ctx["public_id"]}/billing/reviews/'
        f'{review.public_id}/resolve',
        headers=headers,
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert (await _billing(client, ctx['public_id'])).json()['reviews'] == []
    db_session.expire_all()
    saved = await db_session.get(InfinitePayCheckout, review_id)
    assert saved.status is CheckoutStatus.RESOLVED


@pytest.mark.asyncio
async def test_resolve_paid_checkout_is_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    paid = await _checkout(db_session, ctx['id'], CheckoutStatus.PAID)

    response = await client.post(
        f'/api/v1/students/{ctx["public_id"]}/billing/reviews/'
        f'{paid.public_id}/resolve',
        headers=await auth_headers(client),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'REVIEW_NOT_FOUND'


@pytest.mark.asyncio
async def test_resolve_review_other_academy_404(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _student(db_session, monkeypatch)
    review = await _checkout(db_session, ctx['id'], CheckoutStatus.REVIEW)
    review_id, review_public_id = review.id, review.public_id
    other = await other_academy_headers(db_session)

    response = await client.post(
        f'/api/v1/students/{ctx["public_id"]}/billing/reviews/'
        f'{review_public_id}/resolve',
        headers=other,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    db_session.expire_all()
    saved = await db_session.get(InfinitePayCheckout, review_id)
    assert saved.status is CheckoutStatus.REVIEW
