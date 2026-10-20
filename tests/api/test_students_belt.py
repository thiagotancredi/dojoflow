import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers
from tests.helpers.graduation import (
    create_belt,
    create_student,
    enable_modality,
)


async def _setup(client: AsyncClient, db_session: AsyncSession) -> dict:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    jiu_jitsu = await enable_modality(client, db_session, headers, 'Jiu-jitsu')

    return {
        'headers': headers,
        'taekwondo': taekwondo,
        'jiu_jitsu': jiu_jitsu,
        'white': await create_belt(client, headers, taekwondo, 'Branca'),
        'yellow': await create_belt(client, headers, taekwondo, 'Amarela'),
        'blue_jj': await create_belt(client, headers, jiu_jitsu, 'Azul'),
    }


async def _create(
    client: AsyncClient, ctx: dict, current_belt: dict | None
) -> object:
    enrollment: dict = {'modality_id': ctx['taekwondo']}

    if current_belt is not None:
        enrollment['current_belt'] = current_belt

    return await client.post(
        '/api/v1/students',
        headers=ctx['headers'],
        json={'name': 'Gabriel Rocha', 'enrollment': enrollment},
    )


async def _belts(
    client: AsyncClient, ctx: dict, student_id: str, modality_id: str
) -> dict:
    detail = await client.get(
        f'/api/v1/students/{student_id}', headers=ctx['headers']
    )
    enrollment = next(
        item
        for item in detail.json()['enrollments']
        if item['modality_id'] == modality_id
    )
    response = await client.get(
        f'/api/v1/students/{student_id}/enrollments/{enrollment["id"]}/belts',
        headers=ctx['headers'],
    )

    return response.json()


async def _student_total(client: AsyncClient, ctx: dict) -> int:
    response = await client.get('/api/v1/students', headers=ctx['headers'])

    return response.json()['total']


@pytest.mark.asyncio
async def test_create_student_with_current_belt(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await _create(
        client,
        ctx,
        {'belt_id': ctx['yellow']['id'], 'graduated_on': '2025-03-01'},
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    belts = await _belts(client, ctx, response.json()['id'], ctx['taekwondo'])
    assert belts['current']['belt']['name'] == 'Amarela'
    assert belts['current']['graduated_on'] == '2025-03-01'


@pytest.mark.asyncio
async def test_create_student_without_belt_still_works(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await _create(client, ctx, None)

    assert response.status_code == HTTPStatus.CREATED, response.text
    belts = await _belts(client, ctx, response.json()['id'], ctx['taekwondo'])
    assert belts['history'] == []


@pytest.mark.asyncio
async def test_invalid_belt_creates_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await _create(
        client,
        ctx,
        {'belt_id': ctx['blue_jj']['id'], 'graduated_on': '2025-03-01'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'BELT_MODALITY_MISMATCH'
    assert await _student_total(client, ctx) == 0


@pytest.mark.asyncio
async def test_unknown_belt_is_404_and_creates_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await _create(
        client,
        ctx,
        {'belt_id': str(uuid.uuid4()), 'graduated_on': '2025-03-01'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'BELT_NOT_FOUND'
    assert await _student_total(client, ctx) == 0


@pytest.mark.asyncio
async def test_new_enrollment_with_current_belt(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    student_id, _ = await create_student(
        client, ctx['headers'], ctx['jiu_jitsu']
    )

    response = await client.post(
        f'/api/v1/students/{student_id}/enrollments',
        headers=ctx['headers'],
        json={
            'modality_id': ctx['taekwondo'],
            'current_belt': {
                'belt_id': ctx['white']['id'],
                'graduated_on': '2026-10-20',
            },
        },
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    belts = await _belts(client, ctx, student_id, ctx['taekwondo'])
    assert belts['current']['belt']['name'] == 'Branca'


@pytest.mark.asyncio
async def test_new_enrollment_with_invalid_belt_creates_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    student_id, _ = await create_student(
        client, ctx['headers'], ctx['jiu_jitsu']
    )

    response = await client.post(
        f'/api/v1/students/{student_id}/enrollments',
        headers=ctx['headers'],
        json={
            'modality_id': ctx['taekwondo'],
            'current_belt': {
                'belt_id': ctx['blue_jj']['id'],
                'graduated_on': '2026-10-20',
            },
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    detail = await client.get(
        f'/api/v1/students/{student_id}', headers=ctx['headers']
    )
    assert len(detail.json()['enrollments']) == 1
