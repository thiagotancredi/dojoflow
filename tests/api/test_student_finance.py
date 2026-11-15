"""Ficha do aluno, aba Financeiro: cada cobrança de graduação traz o exame,
a faixa, o link e o WhatsApp da graduação."""

from datetime import date
from http import HTTPStatus
from urllib.parse import unquote

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.services import billing as billing_module
from tests.helpers.auth import auth_headers
from tests.helpers.scenario import (
    add_belt,
    add_graduation_list,
    add_modality,
    add_student,
    generate_charges,
)

LISTS_URL = '/api/v1/graduation-lists'
TODAY = date(2026, 11, 20)


async def _scenario(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Ana (com telefone e mensalidade) em duas listas: Verde (R$ 100,
    exame 30/11) e Azul (R$ 120, exame 14/12)."""
    monkeypatch.setattr(billing_module, 'local_today', lambda: TODAY)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    verde = await add_belt(
        db_session, taekwondo, 'Verde', primary_color='#2e8b3a', price='100'
    )
    azul = await add_belt(
        db_session, taekwondo, 'Azul', primary_color='#2563a8', price='120'
    )
    student_id, enrollment_id = await add_student(
        db_session,
        taekwondo,
        'Ana Lima',
        phone='62988880002',
        monthly_fee='110',
        due_day=10,
        billing_start_month='2026-11-01',
    )
    lists = {}
    for name, exam, deadline, belt in (
        ('Exame de novembro', '2026-11-30', '2026-11-28', verde),
        ('Exame de dezembro', '2026-12-14', '2026-12-05', azul),
    ):
        lists[name] = await add_graduation_list(
            db_session, taekwondo, exam, name=name, payment_due_date=deadline
        )
        response = await client.post(
            f'{LISTS_URL}/{lists[name]["id"]}/entries',
            headers=headers,
            json={
                'enrollment_id': enrollment_id,
                'target_belt_id': belt['id'],
            },
        )
        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

    return {'headers': headers, 'student_id': student_id, 'lists': lists}


async def _charges(client: AsyncClient, ctx: dict) -> list[dict]:
    response = await client.get(
        f'/api/v1/students/{ctx["student_id"]}/billing', headers=ctx['headers']
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()['charges']


def _graduation(charges: list[dict], belt: str) -> dict:
    return next(
        c
        for c in charges
        if c['kind'] == 'graduation' and c['description'] == belt
    )


@pytest.mark.asyncio
async def test_graduation_charge_has_exam_belt_and_links(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    charge = _graduation(await _charges(client, ctx), 'Verde')
    graduation = charge['graduation']

    assert graduation['list_id'] == ctx['lists']['Exame de novembro']['id']
    assert graduation['list_name'] == 'Exame de novembro'
    assert graduation['exam_date'] == '2026-11-30'
    assert graduation['belt']['name'] == 'Verde'
    assert graduation['belt']['primary_color'] == '#2e8b3a'
    assert graduation['pay_url'].endswith('/graduacao')
    assert graduation['whatsapp_url'].startswith('https://wa.me/')
    assert 'faixa Verde' in unquote(graduation['whatsapp_url'])


@pytest.mark.asyncio
async def test_two_lists_two_cards(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    charges = await _charges(client, ctx)

    assert {
        c['graduation']['list_id']
        for c in charges
        if c['kind'] == 'graduation'
    } == {lst['id'] for lst in ctx['lists'].values()}


@pytest.mark.asyncio
async def test_monthly_charge_has_no_graduation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    await generate_charges(db_session, TODAY)
    monthly = [
        c for c in await _charges(client, ctx) if c['kind'] == 'monthly'
    ]

    assert monthly
    assert all(c['graduation'] is None for c in monthly)


@pytest.mark.asyncio
async def test_paid_graduation_has_no_whatsapp(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    ctx = await _scenario(client, db_session, monkeypatch)
    charge = _graduation(await _charges(client, ctx), 'Verde')
    response = await client.post(
        f'/api/v1/students/{ctx["student_id"]}/billing/payments',
        headers=ctx['headers'],
        json={
            'amount': '100',
            'paid_on': '2026-11-15',
            'method': 'pix',
            'group': 'graduation',
            'charge_id': charge['id'],
        },
    )
    assert response.status_code == HTTPStatus.CREATED, response.text

    paid = _graduation(await _charges(client, ctx), 'Verde')
    assert paid['status'] == 'paid'
    assert paid['graduation']['whatsapp_url'] is None
