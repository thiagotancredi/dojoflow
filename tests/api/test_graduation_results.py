"""Resultado do exame na lista de graduação: aprovar grava a faixa alvo e as
puladas na ficha, com a data escolhida; reprovar não mexe em nada;
desfazer apaga só o que a aprovação gravou."""

from datetime import date
from decimal import Decimal
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.graduation_list import GraduationListEntry
from dojoflow.models.payment import Payment
from dojoflow.services import graduation_result as result_module
from dojoflow.shared.enums import PaymentStatus
from tests.helpers.auth import auth_headers, other_academy_headers
from tests.helpers.scenario import (
    add_belt,
    add_belt_record,
    add_graduation_list,
    add_modality,
    add_student,
    db_id,
)

LISTS_URL = '/api/v1/graduation-lists'
EXAM = '2026-11-14'
DEADLINE = '2026-11-30'
TODAY = date(2026, 11, 15)


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(result_module, 'local_today', lambda: TODAY)


async def _setup(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    deadline: str | None = DEADLINE,
) -> dict:
    """Taekwondo: Branca, Amarela, Laranja (R$ 100), Verde (R$ 100).
    Ana e Caio na Amarela desde 2026-05-01; Bruno sem faixa."""
    taekwondo = await add_modality(db_session, 'Taekwondo')
    belts = {
        'Branca': await add_belt(db_session, taekwondo, 'Branca'),
        'Amarela': await add_belt(db_session, taekwondo, 'Amarela'),
        'Laranja': await add_belt(
            db_session, taekwondo, 'Laranja', price='100'
        ),
        'Verde': await add_belt(db_session, taekwondo, 'Verde', price='100'),
    }
    students = {
        name: await add_student(db_session, taekwondo, name)
        for name in ('Ana Lima', 'Bruno Costa', 'Caio Souza')
    }
    await add_belt_record(
        db_session, students['Ana Lima'], belts['Amarela'], '2026-05-01'
    )
    await add_belt_record(
        db_session, students['Caio Souza'], belts['Amarela'], '2026-05-01'
    )
    listing = await add_graduation_list(
        db_session, taekwondo, EXAM, payment_due_date=deadline
    )
    return {
        'db': db_session,
        'headers': await auth_headers(client),
        'belts': belts,
        'students': students,
        'list_url': f'{LISTS_URL}/{listing["id"]}',
    }


async def _add(client: AsyncClient, ctx: dict, student: str, belt: str) -> str:
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
    return (await _entry(client, ctx, student))['id']


async def _entry(client: AsyncClient, ctx: dict, student: str) -> dict:
    detail = await client.get(ctx['list_url'], headers=ctx['headers'])
    assert detail.status_code == HTTPStatus.OK, detail.text
    return next(
        e for e in detail.json()['entries'] if e['student_name'] == student
    )


async def _set_charge(
    ctx: dict, entry_id: str, status: PaymentStatus, paid: str
) -> None:
    """Muda a cobrança da entrada direto no banco (baixa tem teste próprio)."""
    db = ctx['db']
    entry_db_id = await db_id(db, GraduationListEntry, entry_id)
    await db.execute(
        update(Payment)
        .where(Payment.graduation_entry_id == entry_db_id)
        .values(status=status, amount_paid=Decimal(paid))
    )
    await db.commit()


async def _pay(ctx: dict, entry_id: str) -> None:
    await _set_charge(ctx, entry_id, PaymentStatus.PAID, '100')


async def _history(
    client: AsyncClient, ctx: dict, student: str
) -> list[tuple[str, str]]:
    """Ficha: (faixa, data), da mais antiga para a mais nova."""
    student_id, enrollment_id = ctx['students'][student]
    response = await client.get(
        f'/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts',
        headers=ctx['headers'],
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return [
        (item['belt']['name'], item['graduated_on'])
        for item in reversed(response.json()['history'])
    ]


async def _approve(
    client: AsyncClient,
    ctx: dict,
    entry_id: str,
    approved_on: str = EXAM,
    headers: dict | None = None,
):
    return await client.post(
        f'{ctx["list_url"]}/entries/{entry_id}/approve',
        headers=headers or ctx['headers'],
        json={'approved_on': approved_on},
    )


async def _fail(client: AsyncClient, ctx: dict, entry_id: str):
    return await client.post(
        f'{ctx["list_url"]}/entries/{entry_id}/fail', headers=ctx['headers']
    )


async def _undo(client: AsyncClient, ctx: dict, entry_id: str):
    return await client.delete(
        f'{ctx["list_url"]}/entries/{entry_id}/result', headers=ctx['headers']
    )


def _code(response) -> str:
    return response.json()['code']


@pytest.mark.asyncio
async def test_approve_writes_target_belt_with_date(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    await _pay(ctx, entry)

    response = await _approve(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _history(client, ctx, 'Ana Lima') == [
        ('Amarela', '2026-05-01'),
        ('Laranja', '2026-11-14'),
    ]
    detail = await _entry(client, ctx, 'Ana Lima')
    assert detail['result'] == 'approved'
    assert detail['result_on'] == '2026-11-14'


@pytest.mark.asyncio
async def test_approve_skipping_writes_every_belt_same_date(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Verde')
    await _pay(ctx, entry)

    response = await _approve(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _history(client, ctx, 'Ana Lima') == [
        ('Amarela', '2026-05-01'),
        ('Laranja', '2026-11-14'),
        ('Verde', '2026-11-14'),
    ]


@pytest.mark.asyncio
async def test_approve_without_belt_writes_only_target(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Bruno Costa', 'Laranja')
    await _pay(ctx, entry)

    response = await _approve(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _history(client, ctx, 'Bruno Costa') == [
        ('Laranja', '2026-11-14')
    ]


@pytest.mark.asyncio
async def test_approve_starts_from_current_belt(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Verde')
    await _pay(ctx, entry)
    # Graduou por fora depois de entrar na lista
    await add_belt_record(
        db_session,
        ctx['students']['Ana Lima'],
        ctx['belts']['Laranja'],
        '2026-10-01',
    )

    response = await _approve(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _history(client, ctx, 'Ana Lima') == [
        ('Amarela', '2026-05-01'),
        ('Laranja', '2026-10-01'),
        ('Verde', '2026-11-14'),
    ]


@pytest.mark.asyncio
async def test_approve_requires_paid_or_waived(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')

    open_charge = await _approve(client, ctx, entry)
    assert open_charge.status_code == HTTPStatus.CONFLICT
    assert _code(open_charge) == 'GRADUATION_NOT_PAID'

    await _set_charge(ctx, entry, PaymentStatus.PARTIAL, '40')
    partial = await _approve(client, ctx, entry)
    assert partial.status_code == HTTPStatus.CONFLICT
    assert _code(partial) == 'GRADUATION_NOT_PAID'

    # Isenta pela API (cobrança sem nenhum pagamento)
    caio = await _add(client, ctx, 'Caio Souza', 'Laranja')
    charge = (await _entry(client, ctx, 'Caio Souza'))['charge']
    student_id = ctx['students']['Caio Souza'][0]
    waived = await client.post(
        f'/api/v1/students/{student_id}/billing/charges/{charge["id"]}/waive',
        headers=ctx['headers'],
    )
    assert waived.status_code == HTTPStatus.OK, waived.text
    assert (await _approve(client, ctx, caio)).status_code == (
        HTTPStatus.NO_CONTENT
    )
    assert (
        await db_session.scalar(
            select(Payment.status).where(
                Payment.graduation_entry_id
                == await db_id(db_session, GraduationListEntry, caio)
            )
        )
        == PaymentStatus.WAIVED
    )


@pytest.mark.asyncio
async def test_list_without_charge_can_approve(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session, deadline=None)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')

    response = await _approve(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text


@pytest.mark.asyncio
async def test_approve_date_rules(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    await _pay(ctx, entry)

    future = await _approve(client, ctx, entry, '2026-11-16')
    assert future.status_code == HTTPStatus.CONFLICT
    assert _code(future) == 'APPROVAL_DATE_IN_FUTURE'

    before = await _approve(client, ctx, entry, '2026-04-30')
    assert before.status_code == HTTPStatus.CONFLICT
    assert _code(before) == 'APPROVAL_DATE_BEFORE_CURRENT_BELT'

    today = await _approve(client, ctx, entry, '2026-11-15')
    assert today.status_code == HTTPStatus.NO_CONTENT, today.text
    assert (await _entry(client, ctx, 'Ana Lima'))['result_on'] == (
        '2026-11-15'
    )


@pytest.mark.asyncio
async def test_approve_twice_conflict(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    await _pay(ctx, entry)
    await _approve(client, ctx, entry)

    again = await _approve(client, ctx, entry)

    assert again.status_code == HTTPStatus.CONFLICT
    assert _code(again) == 'RESULT_ALREADY_SET'
    assert await _history(client, ctx, 'Ana Lima') == [
        ('Amarela', '2026-05-01'),
        ('Laranja', '2026-11-14'),
    ]


@pytest.mark.asyncio
async def test_fail_keeps_belt_and_charge(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    charge_before = (await _entry(client, ctx, 'Ana Lima'))['charge']

    response = await _fail(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    detail = await _entry(client, ctx, 'Ana Lima')
    assert detail['result'] == 'failed'
    assert detail['result_on'] is None
    assert detail['charge'] == charge_before
    assert await _history(client, ctx, 'Ana Lima') == [
        ('Amarela', '2026-05-01')
    ]
    again = await _approve(client, ctx, entry)
    assert _code(again) == 'RESULT_ALREADY_SET'


@pytest.mark.asyncio
async def test_undo_approval_removes_awarded_belts(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Verde')
    await _pay(ctx, entry)
    await _approve(client, ctx, entry)

    response = await _undo(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _history(client, ctx, 'Ana Lima') == [
        ('Amarela', '2026-05-01')
    ]
    detail = await _entry(client, ctx, 'Ana Lima')
    assert detail['result'] == 'pending'
    assert detail['result_on'] is None


@pytest.mark.asyncio
async def test_undo_after_manual_delete(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Verde')
    await _pay(ctx, entry)
    await _approve(client, ctx, entry)
    student_id, enrollment_id = ctx['students']['Ana Lima']
    url = f'/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts'
    history = (await client.get(url, headers=ctx['headers'])).json()['history']
    orange = next(i for i in history if i['belt']['name'] == 'Laranja')
    deleted = await client.delete(
        f'{url}/{orange["id"]}', headers=ctx['headers']
    )
    assert deleted.status_code == HTTPStatus.NO_CONTENT, deleted.text

    response = await _undo(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _history(client, ctx, 'Ana Lima') == [
        ('Amarela', '2026-05-01')
    ]


@pytest.mark.asyncio
async def test_undo_failed(client: AsyncClient, db_session: AsyncSession):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    await _fail(client, ctx, entry)

    response = await _undo(client, ctx, entry)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert (await _entry(client, ctx, 'Ana Lima'))['result'] == 'pending'


@pytest.mark.asyncio
async def test_approved_entry_is_locked(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    await _pay(ctx, entry)
    await _approve(client, ctx, entry)
    entry_url = f'{ctx["list_url"]}/entries/{entry}'

    removed = await client.delete(entry_url, headers=ctx['headers'])
    assert removed.status_code == HTTPStatus.CONFLICT
    assert _code(removed) == 'ENTRY_APPROVED'

    retarget = await client.patch(
        entry_url,
        headers=ctx['headers'],
        json={'target_belt_id': ctx['belts']['Verde']['id']},
    )
    assert retarget.status_code == HTTPStatus.CONFLICT
    assert _code(retarget) == 'ENTRY_APPROVED'

    deleted = await client.delete(ctx['list_url'], headers=ctx['headers'])
    assert deleted.status_code == HTTPStatus.CONFLICT
    assert _code(deleted) == 'LIST_HAS_APPROVED'


@pytest.mark.asyncio
async def test_failed_entry_can_be_removed(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    await _fail(client, ctx, entry)

    response = await client.delete(
        f'{ctx["list_url"]}/entries/{entry}', headers=ctx['headers']
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text


@pytest.mark.asyncio
async def test_entry_from_other_list_not_found(
    client: AsyncClient, db_session: AsyncSession
):
    ctx = await _setup(client, db_session)
    entry = await _add(client, ctx, 'Ana Lima', 'Laranja')
    await _pay(ctx, entry)
    taekwondo_id = (
        await client.get(ctx['list_url'], headers=ctx['headers'])
    ).json()['summary']['modality']['id']
    other = await add_graduation_list(
        db_session, taekwondo_id, EXAM, name='Outra'
    )
    other_ctx = {**ctx, 'list_url': f'{LISTS_URL}/{other["id"]}'}

    for response in (
        await _approve(client, other_ctx, entry),
        await _fail(client, other_ctx, entry),
        await _undo(client, other_ctx, entry),
        await _approve(
            client,
            ctx,
            entry,
            headers=await other_academy_headers(db_session),
        ),
    ):
        assert response.status_code == HTTPStatus.NOT_FOUND, response.text

    assert (await _entry(client, ctx, 'Ana Lima'))['result'] == 'pending'
