"""Cobranças de graduação acompanham a lista (entra, sai, faixa, data,
preço)."""

from datetime import date
from decimal import Decimal
from http import HTTPStatus
from urllib.parse import unquote
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.graduation_list import GraduationList
from dojoflow.models.modality import Modality
from dojoflow.models.payment import Payment
from dojoflow.models.student import Student
from dojoflow.services import billing as billing_module
from dojoflow.shared.enums import PaymentKind, PaymentStatus
from tests.helpers.auth import auth_headers
from tests.helpers.scenario import (
    add_belt,
    add_graduation_list,
    add_modality,
    add_responsible,
    add_student,
)

LISTS_URL = '/api/v1/graduation-lists'
EXAM = '2026-12-14'
DEADLINE = '2026-12-05'


async def _setup(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    deadline: str | None = DEADLINE,
) -> dict:
    """Taekwondo: Branca (grátis), Verde (R$ 100), Azul (R$ 120); 3 alunos;
    uma lista com data limite (ou sem)."""
    taekwondo = await add_modality(db_session, 'Taekwondo')
    belts = {
        'Branca': await add_belt(db_session, taekwondo, 'Branca'),
        'Verde': await add_belt(db_session, taekwondo, 'Verde', price='100'),
        'Azul': await add_belt(db_session, taekwondo, 'Azul', price='120'),
    }
    students = {
        name: await add_student(db_session, taekwondo, name)
        for name in ('Ana Lima', 'Bruno Costa', 'Caio Souza')
    }
    listing = await add_graduation_list(
        db_session, taekwondo, EXAM, payment_due_date=deadline
    )
    return {
        'headers': await auth_headers(client),
        'belts': belts,
        'students': students,
        'list_url': f'{LISTS_URL}/{listing["id"]}',
    }


async def _add(
    client: AsyncClient, ctx: dict, student: str, belt: str = 'Verde'
) -> str:
    """Põe o aluno na lista; devolve o id da entrada."""
    response = await client.post(
        f'{ctx["list_url"]}/entries',
        headers=ctx['headers'],
        json={
            'enrollment_id': ctx['students'][student][1],
            'target_belt_id': ctx['belts'][belt]['id'],
        },
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    detail = await client.get(ctx['list_url'], headers=ctx['headers'])
    return next(
        e['id']
        for e in detail.json()['entries']
        if e['student_name'] == student
    )


async def _modality_id(db_session: AsyncSession, ctx: dict) -> str:
    list_id = UUID(ctx['list_url'].rsplit('/', 1)[1])
    return str(
        await db_session.scalar(
            select(Modality.public_id)
            .join(GraduationList, GraduationList.modality_id == Modality.id)
            .where(GraduationList.public_id == list_id)
        )
    )


async def _charges(db_session: AsyncSession) -> list[Payment]:
    db_session.expire_all()
    return list(
        (
            await db_session.scalars(
                select(Payment)
                .where(Payment.kind == PaymentKind.GRADUATION)
                .order_by(Payment.id)
            )
        ).all()
    )


async def _mark_paid(
    db_session: AsyncSession, charge_id: int, paid: str
) -> None:
    amount = Decimal(paid)
    charge = await db_session.get(Payment, charge_id)
    status = (
        PaymentStatus.PAID
        if amount >= (charge.amount_due or 0)
        else PaymentStatus.PARTIAL
    )
    await db_session.execute(
        update(Payment)
        .where(Payment.id == charge_id)
        .values(amount_paid=amount, status=status)
    )
    await db_session.commit()


async def _patch_list(client: AsyncClient, ctx: dict, **values) -> None:
    response = await client.patch(
        ctx['list_url'], headers=ctx['headers'], json=values
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.text


async def _set_price(client: AsyncClient, ctx: dict, belt: str, price: str):
    response = await client.put(
        f'/api/v1/academy/belts/{ctx["belts"][belt]["id"]}',
        headers=ctx['headers'],
        json={'name': belt, 'primary_color': '#2e8b3a', 'price': price},
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return response


@pytest.mark.asyncio
async def test_entry_with_priced_belt_gets_charge(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)

    await _add(client, ctx, 'Ana Lima')

    (charge,) = await _charges(db_session)
    assert charge.amount_due == Decimal('100.00')
    assert charge.due_date == date(2026, 12, 5)
    assert charge.reference_month == date(2026, 12, 1)
    assert charge.description == 'Verde'
    assert charge.status is PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_free_belt_no_charge(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)

    await _add(client, ctx, 'Ana Lima', belt='Branca')

    assert await _charges(db_session) == []


@pytest.mark.asyncio
async def test_no_deadline_no_charge(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session, deadline=None)

    await _add(client, ctx, 'Ana Lima')

    assert await _charges(db_session) == []


@pytest.mark.asyncio
async def test_deadline_set_later_creates_for_everyone(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session, deadline=None)
    await _add(client, ctx, 'Ana Lima')
    await _add(client, ctx, 'Bruno Costa', belt='Azul')
    await _add(client, ctx, 'Caio Souza', belt='Branca')

    await _patch_list(client, ctx, payment_due_date=DEADLINE)

    charges = await _charges(db_session)
    assert sorted(c.amount_due for c in charges) == [
        Decimal('100.00'),
        Decimal('120.00'),
    ]


@pytest.mark.asyncio
async def test_clearing_deadline_keeps_paid_drops_open(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await _add(client, ctx, 'Ana Lima')
    await _add(client, ctx, 'Bruno Costa')
    paid, _ = await _charges(db_session)
    await _mark_paid(db_session, paid.id, '100')

    await _patch_list(client, ctx, payment_due_date=None)

    (kept,) = await _charges(db_session)
    assert kept.id == paid.id
    assert kept.status is PaymentStatus.PAID


@pytest.mark.asyncio
async def test_new_deadline_moves_open_charges(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await _add(client, ctx, 'Ana Lima')

    await _patch_list(client, ctx, payment_due_date='2027-01-08')

    (charge,) = await _charges(db_session)
    assert charge.due_date == date(2027, 1, 8)
    assert charge.reference_month == date(2027, 1, 1)


@pytest.mark.asyncio
async def test_retarget_updates_open_amount(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    entry_id = await _add(client, ctx, 'Ana Lima')
    entry_url = f'{ctx["list_url"]}/entries/{entry_id}'

    response = await client.patch(
        entry_url,
        headers=ctx['headers'],
        json={'target_belt_id': ctx['belts']['Azul']['id']},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    (charge,) = await _charges(db_session)
    assert charge.amount_due == Decimal('120.00')
    assert charge.description == 'Azul'

    response = await client.patch(
        entry_url,
        headers=ctx['headers'],
        json={'target_belt_id': ctx['belts']['Branca']['id']},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _charges(db_session) == []


@pytest.mark.asyncio
async def test_price_change_updates_open_not_paid(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await _add(client, ctx, 'Ana Lima')
    await _add(client, ctx, 'Bruno Costa')
    paid, _ = await _charges(db_session)
    await _mark_paid(db_session, paid.id, '100')

    await _set_price(client, ctx, 'Verde', '90')

    amounts = {c.id: c.amount_due for c in await _charges(db_session)}
    assert amounts[paid.id] == Decimal('100.00')
    assert sorted(amounts.values()) == [Decimal('90.00'), Decimal('100.00')]


@pytest.mark.asyncio
async def test_price_below_partial_payment_becomes_paid(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await _add(client, ctx, 'Ana Lima')
    (charge,) = await _charges(db_session)
    await _mark_paid(db_session, charge.id, '60')

    await _set_price(client, ctx, 'Verde', '50')

    (charge,) = await _charges(db_session)
    assert charge.status is PaymentStatus.PAID
    assert charge.amount_due == Decimal('60.00')
    assert charge.amount_paid == Decimal('60.00')


@pytest.mark.asyncio
async def test_remove_entry_drops_unpaid_keeps_paid(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    ana = await _add(client, ctx, 'Ana Lima')
    bruno = await _add(client, ctx, 'Bruno Costa')
    paid, _ = await _charges(db_session)
    await _mark_paid(db_session, paid.id, '100')

    for entry_id in (ana, bruno):
        response = await client.delete(
            f'{ctx["list_url"]}/entries/{entry_id}', headers=ctx['headers']
        )
        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

    (kept,) = await _charges(db_session)
    assert kept.id == paid.id
    assert kept.graduation_entry_id is None


@pytest.mark.asyncio
async def test_delete_list_drops_unpaid_keeps_paid(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await _add(client, ctx, 'Ana Lima')
    await _add(client, ctx, 'Bruno Costa')
    paid, _ = await _charges(db_session)
    await _mark_paid(db_session, paid.id, '100')

    response = await client.delete(ctx['list_url'], headers=ctx['headers'])

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    (kept,) = await _charges(db_session)
    assert kept.id == paid.id


@pytest.mark.asyncio
async def test_list_api_reads_and_clears_payment_due_date(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    taekwondo = await add_modality(db_session, 'Taekwondo')
    await add_belt(db_session, taekwondo, 'Branca')
    headers = await auth_headers(client)

    created = await client.post(
        LISTS_URL,
        headers=headers,
        json={
            'name': 'Dezembro',
            'modality_id': taekwondo,
            'exam_date': EXAM,
            'payment_due_date': DEADLINE,
        },
    )
    assert created.status_code == HTTPStatus.CREATED, created.text
    assert created.json()['payment_due_date'] == DEADLINE

    url = f'{LISTS_URL}/{created.json()["id"]}'
    cleared = await client.patch(
        url, headers=headers, json={'payment_due_date': None}
    )
    assert cleared.status_code == HTTPStatus.NO_CONTENT, cleared.text
    detail = await client.get(url, headers=headers)
    assert detail.json()['summary']['payment_due_date'] is None


@pytest.mark.asyncio
async def test_belt_price_round_trip_and_validation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)

    saved = await _set_price(client, ctx, 'Branca', '75.5')
    assert saved.json()['price'] == '75.50'

    rejected = await client.put(
        f'/api/v1/academy/belts/{ctx["belts"]["Branca"]["id"]}',
        headers=ctx['headers'],
        json={'name': 'Branca', 'primary_color': '#ffffff', 'price': '-1'},
    )
    assert rejected.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def _detail_entries(client: AsyncClient, ctx: dict) -> dict:
    detail = await client.get(ctx['list_url'], headers=ctx['headers'])
    assert detail.status_code == HTTPStatus.OK, detail.text
    return {e['student_name']: e for e in detail.json()['entries']}


@pytest.fixture
def freeze_today(monkeypatch: pytest.MonkeyPatch):
    def freeze(day: date) -> None:
        monkeypatch.setattr(billing_module, 'local_today', lambda: day)

    return freeze


@pytest.mark.asyncio
async def test_detail_shows_charge_per_entry(
    client: AsyncClient, db_session: AsyncSession, freeze_today
) -> None:
    freeze_today(date(2026, 11, 20))
    ctx = await _setup(client, db_session)
    await _add(client, ctx, 'Ana Lima')
    await _add(client, ctx, 'Bruno Costa')
    await _add(client, ctx, 'Caio Souza', belt='Branca')
    _, bruno = await _charges(db_session)
    await _mark_paid(db_session, bruno.id, '100')
    await db_session.execute(
        update(Payment)
        .where(Payment.id == bruno.id)
        .values(paid_at=date(2026, 11, 18))
    )
    await db_session.commit()

    entries = await _detail_entries(client, ctx)

    ana = entries['Ana Lima']['charge']
    assert ana['open_amount'] == '100.00'
    assert ana['status'] == 'upcoming'
    assert ana['due_date'] == DEADLINE
    assert ana['days_late'] == 0
    paid = entries['Bruno Costa']['charge']
    assert paid['status'] == 'paid'
    assert paid['paid_at'] == '2026-11-18'
    assert entries['Bruno Costa']['whatsapp_url'] is None
    assert entries['Caio Souza']['charge'] is None
    assert entries['Ana Lima']['student_id'] == ctx['students']['Ana Lima'][0]


@pytest.mark.asyncio
async def test_overdue_entry_has_days_late(
    client: AsyncClient, db_session: AsyncSession, freeze_today
) -> None:
    freeze_today(date(2026, 12, 8))
    ctx = await _setup(client, db_session)
    await _add(client, ctx, 'Ana Lima')

    charge = (await _detail_entries(client, ctx))['Ana Lima']['charge']

    assert charge['status'] == 'overdue'
    assert charge['days_late'] == 3  # noqa: PLR2004


@pytest.mark.asyncio
async def test_graduation_whatsapp_text(
    client: AsyncClient, db_session: AsyncSession, freeze_today
) -> None:
    freeze_today(date(2026, 11, 20))
    ctx = await _setup(client, db_session)
    await db_session.execute(
        update(Student)
        .where(Student.public_id == UUID(ctx['students']['Ana Lima'][0]))
        .values(phone='62999990001')
    )
    minor = await add_student(
        db_session,
        await _modality_id(db_session, ctx),
        'Duda Reis',
        birth_date='2015-03-01',
    )
    ctx['students']['Duda Reis'] = minor
    await add_responsible(db_session, minor[0], name='Inimar Reis')
    await db_session.commit()
    await _add(client, ctx, 'Ana Lima')
    await _add(client, ctx, 'Duda Reis')

    entries = await _detail_entries(client, ctx)

    url = entries['Ana Lima']['whatsapp_url']
    assert url.startswith('https://wa.me/5562999990001?text=')
    text = unquote(url.split('?text=', 1)[1])
    assert text.startswith('Olá, Ana! Tudo bem?')
    assert (
        'O valor da graduação para a faixa Verde (Taekwondo) é R$ 100,00, '
        'com pagamento até 05/12.'
    ) in text
    assert '/graduacao\n' in text
    assert entries['Duda Reis']['responsible_name'] == 'Inimar Reis'
    assert 'Olá, Inimar!' in unquote(entries['Duda Reis']['whatsapp_url'])
