import uuid
from datetime import date
from decimal import Decimal
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.payment import Payment
from dojoflow.models.payment_allocation import PaymentAllocation
from dojoflow.core.settings import settings
from dojoflow.models.payment_transaction import PaymentTransaction
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.services.billing import BillingService
from tests.helpers.auth import auth_headers, other_academy_headers
from tests.helpers.scenario import (
    add_modality,
    add_responsible,
    add_student,
)


def _freeze_today(monkeypatch: pytest.MonkeyPatch, today: date) -> None:
    monkeypatch.setattr(billing_module, 'local_today', lambda: today)


def _url(student_id: str) -> str:
    return f'/api/v1/students/{student_id}/billing'


async def _read(
    client: AsyncClient, student_id: str, headers: dict[str, str]
) -> dict:
    response = await client.get(_url(student_id), headers=headers)
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()


@pytest.mark.asyncio
async def test_generation_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, enrollment_id = await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
    )
    _freeze_today(monkeypatch, date(2027, 3, 2))

    await _read(client, student_id, headers)
    body = await _read(client, student_id, headers)

    # Mais nova em cima: março, fevereiro, janeiro
    assert [c['reference_month'] for c in body['charges']] == [
        '2027-03-01',
        '2027-02-01',
        '2027-01-01',
    ]
    march = body['charges'][0]
    assert march['kind'] == 'monthly'
    assert march['enrollment_id'] == enrollment_id
    assert march['modality_name'] == 'Taekwondo'
    assert march['due_date'] == '2027-03-15'
    assert march['amount'] == '100.00'
    assert march['paid'] == '0.00'
    assert march['status'] == 'upcoming'
    assert body['charges'][1]['status'] == 'overdue'
    assert body['open_total'] == '300.00'
    assert body['open_months'] == 'janeiro, fevereiro e março'
    assert body['whatsapp_url'] is None
    assert body['payments'] == []

    total = await db_session.scalar(select(func.count()).select_from(Payment))
    assert total == 3  # noqa: PLR2004


@pytest.mark.asyncio
async def test_first_monthly_charge_is_next_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Matrícula em 20/10/2026, vencimento dia 10: a cobrança começa em
    # novembro (a taxa de matrícula entra na Tarefa 6)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        monthly_fee='120',
        due_day=10,
        billing_start_month='2026-11-01',
    )

    _freeze_today(monkeypatch, date(2026, 10, 20))
    body = await _read(client, student_id, headers)
    assert body['charges'] == []
    assert body['open_total'] == '0.00'
    assert not body['open_months']

    _freeze_today(monkeypatch, date(2026, 11, 1))
    body = await _read(client, student_id, headers)
    assert len(body['charges']) == 1
    november = body['charges'][0]
    assert november['reference_month'] == '2026-11-01'
    assert november['due_date'] == '2026-11-10'
    assert november['amount'] == '120.00'
    assert november['status'] == 'upcoming'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'kwargs',
    [
        {'status': 'inactive', 'monthly_fee': '100', 'due_day': 15},
        {'is_exempt': True, 'monthly_fee': '100', 'due_day': 15},
        {'monthly_fee': None, 'due_day': 15},
        {'monthly_fee': '100', 'due_day': None},
    ],
    ids=['inactive', 'exempt', 'no-fee', 'no-due-day'],
)
async def test_inactive_or_exempt_enrollment_generates_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict,
):
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        billing_start_month='2027-01-01',
        **kwargs,
    )
    _freeze_today(monkeypatch, date(2027, 3, 2))

    body = await _read(client, student_id, headers)

    assert body['charges'] == []


@pytest.mark.asyncio
async def test_billing_is_scoped_to_academy(
    client: AsyncClient, db_session: AsyncSession
):
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
    )
    other_headers = await other_academy_headers(db_session)

    response = await client.get(_url(student_id), headers=other_headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'STUDENT_NOT_FOUND'


@pytest.mark.asyncio
async def test_job_generates_for_every_academy(db_session: AsyncSession):
    taekwondo = await add_modality(db_session, 'Taekwondo')
    other = Academy(name='Outra Academia')
    db_session.add(other)
    await db_session.commit()
    await add_modality(db_session, 'Judô', academy_id=other.id)
    await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-03-01',
    )
    await add_student(
        db_session,
        taekwondo,
        name='Bruno Dias',
        monthly_fee='90',
        due_day=5,
        billing_start_month='2027-03-01',
        academy_id=other.id,
    )
    service = BillingService(db_session=db_session)

    created = await service.ensure_monthly_charges(None, date(2027, 3, 1))
    again = await service.ensure_monthly_charges(None, date(2027, 3, 1))

    assert created == 2  # noqa: PLR2004
    assert again == 0


async def _billing_student(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Aluno cobrando desde março/2027 (vencimento dia 15), hoje 02/03."""
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, enrollment_id = await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-03-01',
    )
    _freeze_today(monkeypatch, date(2027, 3, 2))
    body = await _read(client, student_id, headers)

    return {
        'headers': headers,
        'student_id': student_id,
        'enrollment_id': enrollment_id,
        'march': body['charges'][0],
        'url': _url(student_id),
    }


async def _launch(client: AsyncClient, ctx: dict, month: str, **extra):
    return await client.post(
        f'{ctx["url"]}/charges',
        headers=ctx['headers'],
        json={
            'enrollment_id': ctx['enrollment_id'],
            'reference_month': month,
            'amount': '90',
            'due_date': month[:8] + '15',
            **extra,
        },
    )


async def _pay_directly(
    db_session: AsyncSession, charge_public_id: str, amount: str
) -> None:
    # A baixa pela API entra na Tarefa 5; aqui ela é gravada direto
    charge = await db_session.scalar(
        select(Payment).where(Payment.public_id == uuid.UUID(charge_public_id))
    )
    enrollment = await db_session.get(Enrollment, charge.enrollment_id)
    transaction = PaymentTransaction(
        academy_id=charge.academy_id,
        student_id=enrollment.student_id,
        gross_amount=Decimal(amount),
        received_at=date(2027, 3, 2),
    )
    db_session.add(transaction)
    await db_session.flush()
    db_session.add(
        PaymentAllocation(
            academy_id=charge.academy_id,
            payment_transaction_id=transaction.id,
            payment_id=charge.id,
            allocated_amount=Decimal(amount),
        )
    )
    charge.amount_paid = Decimal(amount)
    await db_session.commit()


@pytest.mark.asyncio
async def test_launch_past_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)

    response = await _launch(client, ctx, '2027-01-01')

    assert response.status_code == HTTPStatus.CREATED, response.text
    charge = response.json()
    assert charge['reference_month'] == '2027-01-01'
    assert charge['due_date'] == '2027-01-15'
    assert charge['amount'] == '90.00'
    assert charge['kind'] == 'monthly'
    assert charge['status'] == 'overdue'
    assert charge['enrollment_id'] == ctx['enrollment_id']

    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert [c['reference_month'] for c in body['charges']] == [
        '2027-03-01',
        '2027-01-01',
    ]
    assert body['open_total'] == '190.00'


@pytest.mark.asyncio
async def test_launch_existing_month_conflicts(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)
    first = await _launch(client, ctx, '2027-01-01')
    assert first.status_code == HTTPStatus.CREATED

    again = await _launch(client, ctx, '2027-01-01')

    assert again.status_code == HTTPStatus.CONFLICT
    assert again.json()['code'] == 'CHARGE_ALREADY_EXISTS'


@pytest.mark.asyncio
async def test_launch_month_not_before_billing_start_conflicts(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)

    response = await _launch(client, ctx, '2027-04-01')

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'CHARGE_NOT_PAST'


@pytest.mark.asyncio
async def test_launch_rejects_month_not_on_first_day(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)

    response = await _launch(client, ctx, '2027-01-10')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_launch_for_enrollment_of_other_student_is_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)
    judo = await add_modality(db_session, 'Judô')
    _, other_enrollment = await add_student(
        db_session, judo, name='Bruno Dias'
    )

    response = await _launch(
        client, ctx, '2027-01-01', enrollment_id=other_enrollment
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'ENROLLMENT_NOT_FOUND'


@pytest.mark.asyncio
async def test_waive_and_unwaive(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)
    waive_url = f'{ctx["url"]}/charges/{ctx["march"]["id"]}/waive'

    waived = await client.post(waive_url, headers=ctx['headers'])

    assert waived.status_code == HTTPStatus.OK, waived.text
    assert waived.json()['status'] == 'waived'
    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert body['open_total'] == '0.00'

    restored = await client.delete(waive_url, headers=ctx['headers'])

    assert restored.status_code == HTTPStatus.OK, restored.text
    assert restored.json()['status'] == 'upcoming'
    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert body['open_total'] == '100.00'


@pytest.mark.asyncio
async def test_edit_charge_without_payments(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)

    response = await client.patch(
        f'{ctx["url"]}/charges/{ctx["march"]["id"]}',
        headers=ctx['headers'],
        json={'amount': '80', 'due_date': '2027-03-20'},
    )

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['amount'] == '80.00'
    assert response.json()['due_date'] == '2027-03-20'

    only_amount = await client.patch(
        f'{ctx["url"]}/charges/{ctx["march"]["id"]}',
        headers=ctx['headers'],
        json={'amount': '85'},
    )
    assert only_amount.json()['amount'] == '85.00'
    assert only_amount.json()['due_date'] == '2027-03-20'


@pytest.mark.asyncio
async def test_edit_or_waive_charge_with_payment_conflicts(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)
    await _pay_directly(db_session, ctx['march']['id'], '40')
    charge_url = f'{ctx["url"]}/charges/{ctx["march"]["id"]}'

    edit = await client.patch(
        charge_url, headers=ctx['headers'], json={'amount': '80'}
    )
    waive = await client.post(f'{charge_url}/waive', headers=ctx['headers'])

    assert edit.status_code == HTTPStatus.CONFLICT
    assert edit.json()['code'] == 'CHARGE_HAS_PAYMENTS'
    assert waive.status_code == HTTPStatus.CONFLICT
    assert waive.json()['code'] == 'CHARGE_HAS_PAYMENTS'


@pytest.mark.asyncio
async def test_charge_of_other_student_is_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _billing_student(client, db_session, monkeypatch)
    judo = await add_modality(db_session, 'Judô')
    other_student, _ = await add_student(
        db_session,
        judo,
        name='Bruno Dias',
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-03-01',
    )

    response = await client.post(
        f'{_url(other_student)}/charges/{ctx["march"]["id"]}/waive',
        headers=ctx['headers'],
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'CHARGE_NOT_FOUND'


async def _two_months_student(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Janeiro e fevereiro/2027 de R$ 100 (vencimento dia 15), hoje 20/02."""
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
    )
    _freeze_today(monkeypatch, date(2027, 2, 20))
    body = await _read(client, student_id, headers)
    feb, jan = body['charges']

    return {
        'headers': headers,
        'student_id': student_id,
        'url': _url(student_id),
        'jan': jan,
        'feb': feb,
    }


async def _pay(
    client: AsyncClient, ctx: dict, amount: str, paid_on: str = '2027-02-20'
):
    return await client.post(
        f'{ctx["url"]}/payments',
        headers=ctx['headers'],
        json={'amount': amount, 'paid_on': paid_on, 'method': 'pix'},
    )


def _by_month(body: dict) -> dict:
    return {c['reference_month']: c for c in body['charges']}


@pytest.mark.asyncio
async def test_payment_example_from_spec(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _two_months_student(client, db_session, monkeypatch)

    first = await _pay(client, ctx, '50', paid_on='2027-02-10')
    assert first.status_code == HTTPStatus.CREATED, first.text
    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert _by_month(body)['2027-01-01']['paid'] == '50.00'
    # Parcial e vencida conta como atrasada
    assert _by_month(body)['2027-01-01']['status'] == 'overdue'

    second = await _pay(client, ctx, '150', paid_on='2027-02-20')
    assert second.status_code == HTTPStatus.CREATED, second.text
    payment = second.json()
    assert payment['amount'] == '150.00'
    assert payment['paid_on'] == '2027-02-20'
    assert payment['method'] == 'pix'

    body = await _read(client, ctx['student_id'], ctx['headers'])
    charges = _by_month(body)
    assert charges['2027-01-01']['status'] == 'paid'
    assert charges['2027-02-01']['status'] == 'paid'
    assert body['open_total'] == '0.00'
    # Histórico: a baixa mais nova em cima
    assert [
        [(a['label'], a['amount']) for a in p['allocations']]
        for p in body['payments']
    ] == [
        [('janeiro', '50.00'), ('fevereiro', '100.00')],
        [('janeiro', '50.00')],
    ]
    assert (
        body['payments'][1]['allocations'][0]['charge_id'] == ctx['jan']['id']
    )

    jan = await db_session.scalar(
        select(Payment).where(Payment.public_id == uuid.UUID(ctx['jan']['id']))
    )
    await db_session.refresh(jan)
    assert jan.status.value == 'paid'
    assert jan.paid_at == date(2027, 2, 20)


@pytest.mark.asyncio
async def test_payment_above_open_total_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _two_months_student(client, db_session, monkeypatch)

    response = await _pay(client, ctx, '200.01')

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'PAYMENT_EXCEEDS_OPEN'
    assert 'R$ 200,00' in response.json()['detail']
    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert body['payments'] == []


@pytest.mark.asyncio
async def test_payment_without_open_charges_is_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(db_session, taekwondo)

    response = await client.post(
        f'{_url(student_id)}/payments',
        headers=headers,
        json={'amount': '10', 'paid_on': '2027-02-20'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'NOTHING_TO_PAY'


@pytest.mark.asyncio
async def test_payment_skips_waived_charge(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _two_months_student(client, db_session, monkeypatch)
    await client.post(
        f'{ctx["url"]}/charges/{ctx["jan"]["id"]}/waive',
        headers=ctx['headers'],
    )

    response = await _pay(client, ctx, '100')

    assert response.status_code == HTTPStatus.CREATED, response.text
    assert [a['label'] for a in response.json()['allocations']] == [
        'fevereiro'
    ]


@pytest.mark.asyncio
async def test_delete_payment_restores_previous_balances(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _two_months_student(client, db_session, monkeypatch)
    await _pay(client, ctx, '50', paid_on='2027-02-10')
    second = (await _pay(client, ctx, '120')).json()

    response = await client.delete(
        f'{ctx["url"]}/payments/{second["id"]}', headers=ctx['headers']
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    body = await _read(client, ctx['student_id'], ctx['headers'])
    charges = _by_month(body)
    assert charges['2027-01-01']['paid'] == '50.00'
    assert charges['2027-02-01']['paid'] == '0.00'
    assert charges['2027-02-01']['status'] == 'overdue'
    assert body['open_total'] == '150.00'
    assert len(body['payments']) == 1

    jan = await db_session.scalar(
        select(Payment).where(Payment.public_id == uuid.UUID(ctx['jan']['id']))
    )
    await db_session.refresh(jan)
    assert jan.status.value == 'partial'
    assert jan.paid_at is None


@pytest.mark.asyncio
async def test_preview_matches_payment(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _two_months_student(client, db_session, monkeypatch)

    preview = await client.post(
        f'{ctx["url"]}/payments/preview',
        headers=ctx['headers'],
        json={'amount': '120'},
    )

    assert preview.status_code == HTTPStatus.OK, preview.text
    assert preview.json()['allocations'] == [
        {
            'charge_id': ctx['jan']['id'],
            'label': 'janeiro',
            'amount': '100.00',
            'settles': True,
        },
        {
            'charge_id': ctx['feb']['id'],
            'label': 'fevereiro',
            'amount': '20.00',
            'settles': False,
        },
    ]
    payment = (await _pay(client, ctx, '120')).json()
    assert [(a['charge_id'], a['amount']) for a in payment['allocations']] == [
        (a['charge_id'], a['amount']) for a in preview.json()['allocations']
    ]


@pytest.mark.asyncio
async def test_payment_of_other_student_is_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _two_months_student(client, db_session, monkeypatch)
    payment = (await _pay(client, ctx, '50')).json()
    judo = await add_modality(db_session, 'Judô')
    other_student, _ = await add_student(db_session, judo, name='Bruno Dias')

    response = await client.delete(
        f'{_url(other_student)}/payments/{payment["id"]}',
        headers=ctx['headers'],
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'PAYMENT_NOT_FOUND'


@pytest.mark.asyncio
async def test_new_student_gets_fee_now_and_first_monthly_next_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Cadastro pela API em 20/10/2026 com vencimento dia 10
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    _freeze_today(monkeypatch, date(2026, 10, 20))
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json={
            'name': 'Ana Lima',
            'enrollments': [
                {
                    'modality_id': taekwondo,
                    'monthly_fee': '120',
                    'due_day': 10,
                    'enrollment_fee': '80',
                }
            ],
        },
    )
    assert created.status_code == HTTPStatus.CREATED, created.text
    student_id = created.json()['id']

    body = await _read(client, student_id, headers)
    assert [(c['kind'], c['due_date']) for c in body['charges']] == [
        ('enrollment_fee', '2026-10-20')
    ]

    _freeze_today(monkeypatch, date(2026, 11, 1))
    body = await _read(client, student_id, headers)
    assert [(c['kind'], c['due_date']) for c in body['charges']] == [
        ('monthly', '2026-11-10'),
        ('enrollment_fee', '2026-10-20'),
    ]


async def _overdue_student(  # noqa: PLR0913
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    *,
    name: str = 'Ana Lima',
    phone: str | None = '(62) 99999-0001',
    birth_date: str | None = '1990-05-01',
    modality: str = 'Taekwondo',
) -> dict:
    """Jan e fev/2027 de R$ 100 (dia 15); hoje 20/02: os dois atrasados."""
    headers = await auth_headers(client)
    modality_id = await add_modality(db_session, modality)
    student_id, _ = await add_student(
        db_session,
        modality_id,
        name=name,
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
        phone=phone,
        birth_date=birth_date,
    )
    _freeze_today(monkeypatch, date(2027, 2, 20))
    return {'headers': headers, 'student_id': student_id}


def _message(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    return parsed.path.strip('/'), parse_qs(parsed.query)['text'][0]


@pytest.mark.asyncio
async def test_whatsapp_url_only_for_overdue(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)

    # 10/01: janeiro ainda a vencer → sem link
    _freeze_today(monkeypatch, date(2027, 1, 10))
    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert body['whatsapp_url'] is None

    _freeze_today(monkeypatch, date(2027, 2, 20))
    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert body['whatsapp_url'].startswith('https://wa.me/5562999990001?text=')

    # Tudo pago → sem link de novo
    paid = await _pay(
        client,
        {'headers': ctx['headers'], 'url': _url(ctx['student_id'])},
        '200',
    )
    assert paid.status_code == HTTPStatus.CREATED, paid.text
    body = await _read(client, ctx['student_id'], ctx['headers'])
    assert body['whatsapp_url'] is None


@pytest.mark.asyncio
async def test_whatsapp_without_phone_has_no_link(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch, phone=None)

    body = await _read(client, ctx['student_id'], ctx['headers'])

    assert body['whatsapp_url'] is None


@pytest.mark.asyncio
async def test_whatsapp_goes_to_responsible_for_minor(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(
        client, db_session, monkeypatch, birth_date='2015-03-10'
    )
    await add_responsible(db_session, ctx['student_id'], 'Maria Lima')

    body = await _read(client, ctx['student_id'], ctx['headers'])
    phone, text = _message(body['whatsapp_url'])

    assert phone == '5562988880001'
    assert text.startswith('Olá, Maria!')

    overview = await client.get(
        '/api/v1/billing/overview', headers=ctx['headers']
    )
    (item,) = overview.json()['items']
    assert item['responsible_name'] == 'Maria Lima'


@pytest.mark.asyncio
async def test_whatsapp_adult_goes_to_student(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    await add_responsible(db_session, ctx['student_id'], 'Maria Lima')

    body = await _read(client, ctx['student_id'], ctx['headers'])
    phone, text = _message(body['whatsapp_url'])

    assert phone == '5562999990001'
    assert text.startswith('Olá, Ana!')


@pytest.mark.asyncio
async def test_whatsapp_message_uses_template(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    await client.put(
        '/api/v1/academy/billing-settings',
        headers=ctx['headers'],
        json={
            'pix_key': 'pix@dojo.com',
            'recipient_name': 'Mestre Web',
            'pix_key_type': 'email',
            'message_template': (
                '{nome}|{academia}|{valor}|{meses}|{pix}|{recebedor}|{link}'
            ),
        },
    )

    body = await _read(client, ctx['student_id'], ctx['headers'])
    _, text = _message(body['whatsapp_url'])

    token = await _pay_token(db_session, ctx['student_id'])
    assert text == (
        'Ana|Academia Web Teste|R$ 200,00|janeiro e fevereiro|'
        f'pix@dojo.com|Mestre Web|{settings.WEB_APP_URL}/pagar/{token}'
    )


async def _pay_token(session: AsyncSession, student_id: str) -> str:
    return await session.scalar(
        select(Student.pay_token).where(
            Student.public_id == uuid.UUID(student_id)
        )
    )


@pytest.mark.asyncio
async def test_whatsapp_message_has_pay_link(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)

    body = await _read(client, ctx['student_id'], ctx['headers'])
    _, text = _message(body['whatsapp_url'])

    token = await _pay_token(db_session, ctx['student_id'])
    link = f'{settings.WEB_APP_URL}/pagar/{token}'
    assert f'Para pagar pelo Pix, é só tocar aqui:\n{link}' in text
    assert body['pay_url'] == link


@pytest.mark.asyncio
async def test_custom_template_without_link_gets_it_appended(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    await client.put(
        '/api/v1/academy/billing-settings',
        headers=ctx['headers'],
        json={'message_template': 'Oi, {nome}!'},
    )

    body = await _read(client, ctx['student_id'], ctx['headers'])
    _, text = _message(body['whatsapp_url'])

    token = await _pay_token(db_session, ctx['student_id'])
    assert text == (
        'Oi, Ana!\n\nPara pagar pelo Pix, toque aqui: '
        f'{settings.WEB_APP_URL}/pagar/{token}'
    )


@pytest.mark.asyncio
async def test_overview_counts_and_filters(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ana = await _overdue_student(client, db_session, monkeypatch)
    headers = ana['headers']
    judo = await add_modality(db_session, 'Judô')
    # Bruno: fevereiro vence dia 25 (a vencer, dentro de 7 dias)
    await add_student(
        db_session,
        judo,
        name='Bruno Dias',
        monthly_fee='80',
        due_day=25,
        billing_start_month='2027-02-01',
    )
    # Carla: fevereiro vence dia 10 e foi paga
    carla, _ = await add_student(
        db_session,
        judo,
        name='Carla Reis',
        monthly_fee='90',
        due_day=10,
        billing_start_month='2027-02-01',
    )
    await _read(client, carla, headers)
    paid = await _pay(client, {'headers': headers, 'url': _url(carla)}, '90')
    assert paid.status_code == HTTPStatus.CREATED, paid.text

    url = '/api/v1/billing/overview'
    overdue = (await client.get(url, headers=headers)).json()

    assert overdue['month_expected'] == '270.00'  # fev: 100 + 80 + 90
    assert overdue['month_received'] == '90.00'
    assert overdue['overdue_total'] == '200.00'
    assert overdue['overdue_students'] == 1
    assert overdue['due_soon_total'] == '80.00'
    assert overdue['due_soon_students'] == 1
    assert overdue['total'] == 1
    (item,) = overdue['items']
    assert item['name'] == 'Ana Lima'
    assert item['modalities'] == ['Taekwondo']
    assert item['open_amount'] == '200.00'
    assert item['days_late'] == 36  # noqa: PLR2004  (15/01 → 20/02)
    assert item['whatsapp_url'].startswith('https://wa.me/5562999990001')
    assert item['responsible_name'] is None

    async def names(**params: str) -> list[str]:
        response = await client.get(url, headers=headers, params=params)
        assert response.status_code == HTTPStatus.OK, response.text
        return [i['name'] for i in response.json()['items']]

    assert await names(filter='upcoming') == ['Bruno Dias']
    assert await names(filter='paid') == ['Carla Reis']
    assert await names(filter='all') == [
        'Ana Lima',
        'Bruno Dias',
        'Carla Reis',
    ]
    assert await names(filter='all', search='car') == ['Carla Reis']
    assert await names(filter='all', month='2027-01') == ['Ana Lima']
    assert await names(filter='all', page='2', page_size='2') == ['Carla Reis']
    bad = await client.get(url, headers=headers, params={'month': '2027-13'})
    assert bad.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_overview_is_scoped_to_academy(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await _overdue_student(client, db_session, monkeypatch)
    other_headers = await other_academy_headers(db_session)

    response = await client.get(
        '/api/v1/billing/overview', headers=other_headers
    )

    assert response.json()['items'] == []
    assert response.json()['overdue_total'] == '0.00'


@pytest.mark.asyncio
async def test_overview_open_amount_is_what_the_student_owes(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Ana deve janeiro e fevereiro; no filtro do mês (fevereiro), "Em
    # aberto" mostra tudo o que ela deve, não só fevereiro
    ana = await _overdue_student(client, db_session, monkeypatch)

    response = await client.get(
        '/api/v1/billing/overview',
        headers=ana['headers'],
        params={'filter': 'all', 'month': '2027-02'},
    )

    (item,) = response.json()['items']
    assert item['open_amount'] == '200.00'
    assert item['days_late'] == 36  # noqa: PLR2004


@pytest.mark.asyncio
async def test_overview_lists_students_alphabetically_ignoring_accents(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Todos atrasados, com atrasos diferentes: a ordem é a do nome (A a Z),
    # não a do atraso; acento e maiúscula não mudam a posição
    headers = await auth_headers(client)
    judo = await add_modality(db_session, 'Judô')
    for name, start in (
        ('zeca Lima', '2027-01-01'),
        ('Bruno Dias', '2026-11-01'),
        ('Álvaro Reis', '2027-02-01'),
        ('ana Souza', '2026-12-01'),
    ):
        await add_student(
            db_session,
            judo,
            name=name,
            monthly_fee='100',
            due_day=5,
            billing_start_month=start,
        )
    _freeze_today(monkeypatch, date(2027, 2, 20))

    for filter_name in ('overdue', 'all'):
        response = await client.get(
            '/api/v1/billing/overview',
            headers=headers,
            params={'filter': filter_name},
        )
        names = [item['name'] for item in response.json()['items']]
        assert names == ['Álvaro Reis', 'ana Souza', 'Bruno Dias', 'zeca Lima']
