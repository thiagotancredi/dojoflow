"""Mensalidade e graduação nunca se misturam (números, baixa, links)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.models.payment import Payment
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.services.billing import BillingService
from dojoflow.shared.enums import (
    ChargeGroup,
    CheckoutStatus,
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
)
from dojoflow.shared.exceptions import ConflictError
from tests.helpers.auth import SEED
from tests.helpers.scenario import (
    add_modality,
    add_student,
    db_id,
    generate_charges,
)

TODAY = date(2026, 11, 15)


@pytest.fixture(autouse=True)
def _today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)


async def add_graduation_charge(
    session: AsyncSession,
    enrollment_id: int,
    *,
    amount: str = '100.00',
    due: date = date(2026, 12, 5),
    description: str = 'Verde',
) -> int:
    charge = Payment(
        academy_id=SEED.academy_id,
        enrollment_id=enrollment_id,
        kind=PaymentKind.GRADUATION,
        reference_month=due.replace(day=1),
        due_date=due,
        amount_due=Decimal(amount),
        amount_paid=Decimal('0.00'),
        description=description,
    )
    session.add(charge)
    await session.commit()
    return charge.id


async def _student_with_both(session: AsyncSession) -> tuple[int, int]:
    """Mensalidade de R$ 110 vencida (dia 10) e graduação de R$ 100 aberta
    (vence em dezembro). Devolve (student_id, enrollment_id)."""
    modality = await add_modality(session, 'Taekwondo')
    student, enrollment = await add_student(
        session,
        modality,
        monthly_fee='110',
        due_day=10,
        billing_start_month='2026-11-01',
    )
    await generate_charges(session, TODAY)
    enrollment_id = await db_id(session, Enrollment, enrollment)
    await add_graduation_charge(session, enrollment_id)
    return await db_id(session, Student, student), enrollment_id


async def _status(session: AsyncSession, kind: PaymentKind) -> PaymentStatus:
    session.expire_all()
    return await session.scalar(
        select(Payment.status).where(Payment.kind == kind)
    )


async def _overview(service: BillingService):
    return await service.overview(
        SEED.academy_id,
        month=None,
        status_filter='overdue',
        search=None,
        page=1,
        page_size=20,
    )


@pytest.mark.asyncio
async def test_overview_ignores_graduation(db_session: AsyncSession) -> None:
    modality = await add_modality(db_session, 'Taekwondo')
    _, enrollment = await add_student(
        db_session,
        modality,
        monthly_fee='110',
        due_day=10,
        billing_start_month='2026-11-01',
    )
    await generate_charges(db_session, TODAY)
    service = BillingService(db_session)
    before = await _overview(service)
    dashboard_before = await service.dashboard_lists(SEED.academy_id)

    enrollment_id = await db_id(db_session, Enrollment, enrollment)
    # Uma graduação vencida e outra vencendo em 3 dias
    await add_graduation_charge(
        db_session, enrollment_id, due=date(2026, 11, 12)
    )
    await add_graduation_charge(
        db_session, enrollment_id, due=date(2026, 11, 18), description='Azul'
    )
    after = await _overview(service)
    dashboard_after = await service.dashboard_lists(SEED.academy_id)

    assert after == before
    assert after.overdue_total == Decimal('110.00')
    assert dashboard_after == dashboard_before


@pytest.mark.asyncio
async def test_monthly_payment_never_touches_graduation(
    db_session: AsyncSession,
) -> None:
    student_id, _ = await _student_with_both(db_session)
    service = BillingService(db_session)

    with pytest.raises(ConflictError) as error:
        await service.create_payment(
            SEED.academy_id,
            student_id,
            Decimal('210.00'),
            TODAY,
            PaymentMethod.PIX,
            None,
        )
    assert error.value.code == 'PAYMENT_EXCEEDS_OPEN'

    await service.create_payment(
        SEED.academy_id,
        student_id,
        Decimal('110.00'),
        TODAY,
        PaymentMethod.PIX,
        None,
    )

    monthly = await _status(db_session, PaymentKind.MONTHLY)
    graduation = await _status(db_session, PaymentKind.GRADUATION)

    assert monthly is PaymentStatus.PAID
    assert graduation is PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_graduation_payment_only_graduation(
    db_session: AsyncSession,
) -> None:
    student_id, _ = await _student_with_both(db_session)
    service = BillingService(db_session)

    payment = await service.create_payment(
        SEED.academy_id,
        student_id,
        Decimal('100.00'),
        TODAY,
        PaymentMethod.PIX,
        None,
        group=ChargeGroup.GRADUATION,
    )

    graduation = await _status(db_session, PaymentKind.GRADUATION)
    monthly = await _status(db_session, PaymentKind.MONTHLY)

    assert payment.allocations[0].label == 'Graduação · Verde'
    assert graduation is PaymentStatus.PAID
    assert monthly is PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_graduation_payable_ignores_month_cutoff(
    db_session: AsyncSession,
) -> None:
    student_id, _ = await _student_with_both(db_session)
    service = BillingService(db_session)

    graduation = await service.payable_for_student(
        SEED.academy_id, student_id, TODAY, group=ChargeGroup.GRADUATION
    )
    monthly = await service.payable_for_student(
        SEED.academy_id, student_id, TODAY
    )

    assert [(c.kind, c.amount) for c in graduation] == [
        (PaymentKind.GRADUATION, Decimal('100.00'))
    ]
    assert [c.kind for c in monthly] == [PaymentKind.MONTHLY]


@pytest.mark.asyncio
async def test_received_ignores_graduation(db_session: AsyncSession) -> None:
    student_id, _ = await _student_with_both(db_session)
    service = BillingService(db_session)
    await service.create_payment(
        SEED.academy_id,
        student_id,
        Decimal('100.00'),
        TODAY,
        PaymentMethod.PIX,
        None,
        group=ChargeGroup.GRADUATION,
    )

    overview = await _overview(service)

    assert overview.month_received == Decimal('0.00')


def _checkout(student_id: int, group: ChargeGroup) -> InfinitePayCheckout:
    return InfinitePayCheckout(
        academy_id=SEED.academy_id,
        student_id=student_id,
        handle='katsuflow',
        order_nsu=f'order-{group.value}',
        amount=Decimal('100.00'),
        url=f'https://checkout.example/{group.value}',
        status=CheckoutStatus.OPEN,
        charge_group=group,
    )


@pytest.mark.asyncio
async def test_manual_monthly_payment_keeps_graduation_checkout_open(
    db_session: AsyncSession,
) -> None:
    student_id, _ = await _student_with_both(db_session)
    db_session.add(_checkout(student_id, ChargeGroup.MONTHLY))
    db_session.add(_checkout(student_id, ChargeGroup.GRADUATION))
    await db_session.commit()

    await BillingService(db_session).create_payment(
        SEED.academy_id,
        student_id,
        Decimal('110.00'),
        TODAY,
        PaymentMethod.PIX,
        None,
    )

    db_session.expire_all()
    statuses = dict(
        (
            await db_session.execute(
                select(
                    InfinitePayCheckout.charge_group,
                    InfinitePayCheckout.status,
                )
            )
        ).all()
    )
    assert statuses == {
        ChargeGroup.MONTHLY: CheckoutStatus.CANCELED,
        ChargeGroup.GRADUATION: CheckoutStatus.OPEN,
    }


@pytest.mark.asyncio
async def test_student_billing_lists_graduation_but_totals_monthly(
    db_session: AsyncSession,
) -> None:
    student_id, _ = await _student_with_both(db_session)

    billing = await BillingService(db_session).student_billing(
        SEED.academy_id, student_id, TODAY
    )

    assert {c.kind for c in billing.charges} == {
        PaymentKind.MONTHLY,
        PaymentKind.GRADUATION,
    }
    graduation = next(
        c for c in billing.charges if c.kind is PaymentKind.GRADUATION
    )
    assert graduation.description == 'Verde'
    assert billing.open_total == Decimal('110.00')
    assert billing.open_months == 'novembro'
