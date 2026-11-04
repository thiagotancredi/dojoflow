"""Link /pagar e checkout da InfinitePay só da graduação."""

import uuid
from datetime import date
from decimal import Decimal
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.rate_limit import public_pay_limiter
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.models.payment import Payment
from dojoflow.models.payment_allocation import PaymentAllocation
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.services.infinitepay import InfinitePayService
from dojoflow.shared.enums import (
    ChargeGroup,
    CheckoutStatus,
    PaymentKind,
    PaymentStatus,
    PixKeyType,
)
from tests.helpers.auth import SEED, auth_headers
from tests.helpers.infinitepay import (
    enable_infinitepay,
    fake_infinitepay,
    link_created,
    payment_paid,
)
from tests.helpers.scenario import add_modality, add_student, generate_charges

TODAY = date(2026, 11, 15)
ORDER = 'order-graduation-1'
NEW_LINK = 'https://checkout.infinitepay.io/katsuflow/graduacao'


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    public_pay_limiter.reset()
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)


async def _scenario(session: AsyncSession, monthly_fee: str = '110') -> dict:
    """Ana: mensalidade vencida (dia 10) e graduação de R$ 100 (até 05/12)."""
    modality = await add_modality(session, 'Taekwondo')
    student_public_id, enrollment_public_id = await add_student(
        session,
        modality,
        monthly_fee=monthly_fee,
        due_day=10,
        billing_start_month='2026-11-01',
        phone='62999990001',
    )
    await generate_charges(session, TODAY)
    student = await session.scalar(
        select(Student).where(
            Student.public_id == uuid.UUID(student_public_id)
        )
    )
    enrollment_id = await session.scalar(
        select(Enrollment.id).where(
            Enrollment.public_id == uuid.UUID(enrollment_public_id)
        )
    )
    session.add(
        Payment(
            academy_id=SEED.academy_id,
            enrollment_id=enrollment_id,
            kind=PaymentKind.GRADUATION,
            reference_month=date(2026, 12, 1),
            due_date=date(2026, 12, 5),
            amount_due=Decimal('100.00'),
            amount_paid=Decimal('0.00'),
            description='Verde',
        )
    )
    await session.commit()
    return {'student_id': student.id, 'token': student.pay_token}


async def _pix(session: AsyncSession) -> None:
    session.add(
        AcademyBillingSettings(
            academy_id=SEED.academy_id,
            pix_key='dojo@exemplo.com',
            pix_key_type=PixKeyType.EMAIL,
            pix_city='Goiânia',
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_public_graduation_page_lists_only_graduation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _scenario(db_session)
    await _pix(db_session)
    url = f'/api/v1/public/pay/{ctx["token"]}'

    graduation = await client.get(url, params={'group': 'graduation'})
    monthly = await client.get(url)

    assert graduation.status_code == HTTPStatus.OK, graduation.text
    body = graduation.json()
    assert body['group'] == 'graduation'
    assert [i['label'] for i in body['items']] == ['Graduação · Verde']
    assert body['total'] == '100.00'
    assert '5406100.00' in body['pix_code']
    assert [i['label'] for i in monthly.json()['items']] == [
        'Mensalidade · novembro'
    ]
    assert monthly.json()['group'] == 'monthly'


async def _open_checkout(
    session: AsyncSession, student_id: int, group: ChargeGroup, amount: str
) -> None:
    session.add(
        InfinitePayCheckout(
            academy_id=SEED.academy_id,
            student_id=student_id,
            handle='katsuflow',
            order_nsu=ORDER if group is ChargeGroup.GRADUATION else 'm-1',
            amount=Decimal(amount),
            url=f'https://checkout.infinitepay.io/katsuflow/{group.value}-old',
            status=CheckoutStatus.OPEN,
            charge_group=group,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_graduation_settles_with_monthly_overdue(
    db_session: AsyncSession,
) -> None:
    ctx = await _scenario(db_session)
    await enable_infinitepay(db_session)
    await _open_checkout(
        db_session, ctx['student_id'], ChargeGroup.GRADUATION, '100'
    )

    with fake_infinitepay(payment_paid(amount_cents=10000)) as fake:
        status = await InfinitePayService(db_session, fake.client()).settle(
            ORDER, 'tx-1', 'slug-1'
        )

    assert status is CheckoutStatus.PAID
    db_session.expire_all()
    statuses = dict(
        (await db_session.execute(select(Payment.kind, Payment.status))).all()
    )
    assert statuses == {
        PaymentKind.GRADUATION: PaymentStatus.PAID,
        PaymentKind.MONTHLY: PaymentStatus.PENDING,
    }
    allocated_kinds = (
        await db_session.scalars(
            select(Payment.kind).join(
                PaymentAllocation, PaymentAllocation.payment_id == Payment.id
            )
        )
    ).all()
    assert allocated_kinds == [PaymentKind.GRADUATION]


@pytest.mark.asyncio
async def test_checkout_reuse_respects_group(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Mensalidade de R$ 100: o mesmo valor da graduação
    ctx = await _scenario(db_session, monthly_fee='100')
    await enable_infinitepay(db_session)
    await _open_checkout(
        db_session, ctx['student_id'], ChargeGroup.MONTHLY, '100'
    )

    with fake_infinitepay(link_created(NEW_LINK)) as fake:
        response = await client.post(
            f'/api/v1/public/pay/{ctx["token"]}/checkout',
            params={'group': 'graduation'},
        )

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['url'] == NEW_LINK
    [body] = fake.bodies('/links')
    assert body['redirect_url'].endswith(f'/pagar/{ctx["token"]}/graduacao')
    assert [item['description'] for item in body['items']] == [
        'Graduação · Verde'
    ]
    db_session.expire_all()
    groups = (
        await db_session.scalars(
            select(InfinitePayCheckout.charge_group).order_by(
                InfinitePayCheckout.id
            )
        )
    ).all()
    assert groups == [ChargeGroup.MONTHLY, ChargeGroup.GRADUATION]


async def _student_public_id(session: AsyncSession, student_id: int) -> str:
    return str(
        await session.scalar(
            select(Student.public_id).where(Student.id == student_id)
        )
    )


async def _statuses(session: AsyncSession) -> dict:
    session.expire_all()
    rows = await session.execute(
        select(Student.name, Payment.kind, Payment.status)
        .join(Enrollment, Enrollment.id == Payment.enrollment_id)
        .join(Student, Student.id == Enrollment.student_id)
    )
    return {(name, kind): status for name, kind, status in rows.all()}


@pytest.mark.asyncio
async def test_manual_graduation_payment_api(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _scenario(db_session)
    headers = await auth_headers(client)
    student = await _student_public_id(db_session, ctx['student_id'])
    base = f'/api/v1/students/{student}/billing'

    preview = await client.post(
        f'{base}/payments/preview',
        headers=headers,
        json={'amount': '100', 'group': 'graduation'},
    )
    created = await client.post(
        f'{base}/payments',
        headers=headers,
        json={
            'amount': '100',
            'paid_on': '2026-11-15',
            'method': 'pix',
            'group': 'graduation',
        },
    )

    assert preview.status_code == HTTPStatus.OK, preview.text
    assert [a['label'] for a in preview.json()['allocations']] == [
        'Graduação · Verde'
    ]
    assert created.status_code == HTTPStatus.CREATED, created.text
    statuses = await _statuses(db_session)
    graduation = statuses['Ana Lima', PaymentKind.GRADUATION]
    monthly = statuses['Ana Lima', PaymentKind.MONTHLY]
    assert graduation is PaymentStatus.PAID
    assert monthly is PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_bulk_graduation_payments_api(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ana = await _scenario(db_session)
    modality = await add_modality(db_session, 'Judô')
    bruno_public, bruno_enrollment = await add_student(
        db_session,
        modality,
        'Bruno Costa',
        monthly_fee='90',
        due_day=10,
        billing_start_month='2026-11-01',
    )
    await generate_charges(db_session, TODAY)
    db_session.add(
        Payment(
            academy_id=SEED.academy_id,
            enrollment_id=await db_session.scalar(
                select(Enrollment.id).where(
                    Enrollment.public_id == uuid.UUID(bruno_enrollment)
                )
            ),
            kind=PaymentKind.GRADUATION,
            reference_month=date(2026, 12, 1),
            due_date=date(2026, 12, 5),
            amount_due=Decimal('80.00'),
            amount_paid=Decimal('0.00'),
            description='Amarela',
        )
    )
    await db_session.commit()

    response = await client.post(
        '/api/v1/billing/bulk-payments',
        headers=await auth_headers(client),
        json={
            'paid_on': '2026-11-15',
            'group': 'graduation',
            'items': [
                {
                    'student_id': await _student_public_id(
                        db_session, ana['student_id']
                    ),
                    'amount': '100',
                },
                {'student_id': bruno_public, 'amount': '80'},
            ],
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    statuses = await _statuses(db_session)
    graduation = PaymentKind.GRADUATION
    monthly = PaymentKind.MONTHLY
    assert statuses[('Ana Lima', graduation)] is PaymentStatus.PAID
    assert statuses[('Bruno Costa', graduation)] is PaymentStatus.PAID
    assert statuses[('Ana Lima', monthly)] is PaymentStatus.PENDING
    assert statuses[('Bruno Costa', monthly)] is PaymentStatus.PENDING
