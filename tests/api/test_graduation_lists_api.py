from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality
from tests.helpers.graduation import (
    create_belt,
    create_student,
    enable_modality,
)

LISTS_URL = '/api/v1/graduation-lists'
EXAM_DATE = '2026-11-20'


async def _register_belt(
    client: AsyncClient,
    headers: dict[str, str],
    student: tuple[str, str],
    belt: dict,
    graduated_on: str,
) -> None:
    student_id, enrollment_id = student
    response = await client.post(
        f'/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts',
        headers=headers,
        json={'belt_id': belt['id'], 'graduated_on': graduated_on},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.text


async def _setup(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Taekwondo com Branca, Amarela, Laranja (3 meses cada) e 4 alunos.

    Ana: Branca em 2026-08-20 · Bruno: Branca em 2026-09-01 ·
    Caio: sem faixa · Duda: matrícula inativa.
    """
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    belts = {
        name: await create_belt(
            client,
            headers,
            taekwondo,
            name,
            min_time_amount=3,
            min_time_unit='months',
        )
        for name in ('Branca', 'Amarela', 'Laranja')
    }
    ana = await create_student(client, headers, taekwondo, 'Ana Lima')
    bruno = await create_student(client, headers, taekwondo, 'Bruno Costa')
    caio = await create_student(client, headers, taekwondo, 'Caio Souza')
    duda = await create_student(
        client, headers, taekwondo, 'Duda Reis', status='inactive'
    )
    await _register_belt(client, headers, ana, belts['Branca'], '2026-08-20')
    await _register_belt(client, headers, bruno, belts['Branca'], '2026-09-01')

    return {
        'headers': headers,
        'taekwondo': taekwondo,
        'belts': belts,
        'ana': ana,
        'bruno': bruno,
        'caio': caio,
        'duda': duda,
    }


async def _create_list(
    client: AsyncClient,
    ctx: dict,
    exam_date: str = EXAM_DATE,
) -> dict:
    response = await client.post(
        LISTS_URL,
        headers=ctx['headers'],
        json={
            'name': 'Novembro/2026',
            'modality_id': ctx['taekwondo'],
            'exam_date': exam_date,
        },
    )
    assert response.status_code == HTTPStatus.CREATED, response.text

    return response.json()


async def _detail(client: AsyncClient, ctx: dict, list_id: str) -> dict:
    response = await client.get(
        f'{LISTS_URL}/{list_id}', headers=ctx['headers']
    )
    assert response.status_code == HTTPStatus.OK, response.text

    return response.json()


def _by_name(items: list[dict]) -> dict[str, dict]:
    return {item['student_name']: item for item in items}


@pytest.mark.asyncio
async def test_create_and_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    created = await _create_list(client, ctx)

    assert created['name'] == 'Novembro/2026'
    assert created['modality']['id'] == ctx['taekwondo']
    assert created['modality']['name'] == 'Taekwondo'
    assert created['exam_date'] == EXAM_DATE
    assert created['entry_count'] == 0

    listed = await client.get(LISTS_URL, headers=ctx['headers'])

    assert listed.status_code == HTTPStatus.OK
    assert [item['id'] for item in listed.json()] == [created['id']]


@pytest.mark.asyncio
async def test_create_requires_belts_and_enabled_modality(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    boxing = await enable_modality(client, db_session, headers, 'Boxe')
    judo = str((await create_modality(db_session, 'Judô')).public_id)

    without_belts = await client.post(
        LISTS_URL,
        headers=headers,
        json={'name': 'X', 'modality_id': boxing, 'exam_date': EXAM_DATE},
    )
    not_enabled = await client.post(
        LISTS_URL,
        headers=headers,
        json={
            'name': 'X',
            'modality_id': judo,
            'exam_date': EXAM_DATE,
        },
    )

    assert without_belts.status_code == HTTPStatus.CONFLICT
    assert without_belts.json()['code'] == 'MODALITY_HAS_NO_BELTS'
    assert not_enabled.status_code == HTTPStatus.NOT_FOUND
    assert not_enabled.json()['code'] == 'MODALITY_NOT_ENABLED'


@pytest.mark.asyncio
async def test_detail_lists_active_candidates_with_eligibility(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    created = await _create_list(client, ctx)

    detail = await _detail(client, ctx, created['id'])

    assert detail['summary']['id'] == created['id']
    assert [belt['name'] for belt in detail['belts']] == [
        'Branca',
        'Amarela',
        'Laranja',
    ]
    assert detail['entries'] == []
    assert [item['student_name'] for item in detail['candidates']] == [
        'Ana Lima',
        'Bruno Costa',
        'Caio Souza',
    ]
    candidates = _by_name(detail['candidates'])
    assert candidates['Ana Lima']['enrollment_id'] == ctx['ana'][1]
    assert candidates['Ana Lima']['eligibility'] == 'eligible'
    assert candidates['Ana Lima']['current']['belt']['name'] == 'Branca'
    assert candidates['Ana Lima']['current']['graduated_on'] == '2026-08-20'
    assert candidates['Ana Lima']['suggested_target']['name'] == 'Amarela'
    assert candidates['Bruno Costa']['eligibility'] == 'not_yet'
    assert candidates['Caio Souza']['eligibility'] == 'no_belt'
    assert candidates['Caio Souza']['current'] is None
    assert candidates['Caio Souza']['suggested_target']['name'] == 'Branca'


@pytest.mark.asyncio
async def test_changing_exam_date_recalculates(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    created = await _create_list(client, ctx)

    response = await client.patch(
        f'{LISTS_URL}/{created["id"]}',
        headers=ctx['headers'],
        json={'exam_date': '2026-12-01', 'name': 'Dezembro/2026'},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    detail = await _detail(client, ctx, created['id'])
    assert detail['summary']['exam_date'] == '2026-12-01'
    assert detail['summary']['name'] == 'Dezembro/2026'
    candidates = _by_name(detail['candidates'])
    assert candidates['Bruno Costa']['eligibility'] == 'eligible'


@pytest.mark.asyncio
async def test_patch_rejects_null(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    created = await _create_list(client, ctx)

    response = await client.patch(
        f'{LISTS_URL}/{created["id"]}',
        headers=ctx['headers'],
        json={'name': None},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_delete_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    created = await _create_list(client, ctx)

    deleted = await client.delete(
        f'{LISTS_URL}/{created["id"]}', headers=ctx['headers']
    )

    assert deleted.status_code == HTTPStatus.NO_CONTENT
    gone = await client.get(
        f'{LISTS_URL}/{created["id"]}', headers=ctx['headers']
    )
    assert gone.status_code == HTTPStatus.NOT_FOUND
    assert gone.json()['code'] == 'GRADUATION_LIST_NOT_FOUND'


@pytest.mark.asyncio
async def test_other_academy_cannot_see_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    created = await _create_list(client, ctx)
    other = await auth_headers(
        client, email='outro@dojoflow.test', phone='62988880000'
    )

    response = await client.get(f'{LISTS_URL}/{created["id"]}', headers=other)
    listed = await client.get(LISTS_URL, headers=other)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'GRADUATION_LIST_NOT_FOUND'
    assert listed.json() == []
