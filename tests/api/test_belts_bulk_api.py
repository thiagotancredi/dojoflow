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
    """Taekwondo: Ana e Caio sem faixa, Bruno com Branca, Duda inativa."""
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    jiu_jitsu = await enable_modality(client, db_session, headers, 'Jiu-jitsu')
    white = await create_belt(client, headers, taekwondo, 'Branca')
    yellow = await create_belt(client, headers, taekwondo, 'Amarela')
    ana = await create_student(client, headers, taekwondo, 'Ana Lima')
    bruno = await create_student(client, headers, taekwondo, 'Bruno Costa')
    caio = await create_student(client, headers, taekwondo, 'Caio Souza')
    duda = await create_student(
        client, headers, taekwondo, 'Duda Reis', status='inactive'
    )
    response = await client.post(
        f'/api/v1/students/{bruno[0]}/enrollments/{bruno[1]}/belts',
        headers=headers,
        json={'belt_id': white['id'], 'graduated_on': '2026-01-01'},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    return {
        'headers': headers,
        'taekwondo': taekwondo,
        'jiu_jitsu': jiu_jitsu,
        'white': white,
        'yellow': yellow,
        'ana': ana,
        'bruno': bruno,
        'caio': caio,
        'duda': duda,
        'base': f'/api/v1/academy/modalities/{taekwondo}/belts',
    }


async def _pending(client: AsyncClient, ctx: dict) -> list[dict]:
    response = await client.get(
        f'{ctx["base"]}/pending-enrollments', headers=ctx['headers']
    )
    assert response.status_code == HTTPStatus.OK, response.text

    return response.json()


async def _bulk(client: AsyncClient, ctx: dict, items: list[dict]) -> object:
    return await client.post(
        f'{ctx["base"]}/bulk', headers=ctx['headers'], json={'items': items}
    )


def _item(student: tuple[str, str], belt: dict, graduated_on: str) -> dict:
    return {
        'enrollment_id': student[1],
        'belt_id': belt['id'],
        'graduated_on': graduated_on,
    }


@pytest.mark.asyncio
async def test_pending_lists_active_enrollments_without_belt(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    pending = await _pending(client, ctx)

    assert [item['student_name'] for item in pending] == [
        'Ana Lima',
        'Caio Souza',
    ]
    assert pending[0] == {
        'enrollment_id': ctx['ana'][1],
        'student_id': ctx['ana'][0],
        'student_name': 'Ana Lima',
    }
    options = await client.get(
        '/api/v1/academy/modalities', headers=ctx['headers']
    )
    counts = {
        item['name']: item['pending_belt_count'] for item in options.json()
    }
    assert counts == {'Taekwondo': 2, 'Jiu-jitsu': 0}


@pytest.mark.asyncio
async def test_bulk_saves_all(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await _bulk(
        client,
        ctx,
        [
            _item(ctx['ana'], ctx['yellow'], '2026-07-08'),
            _item(ctx['caio'], ctx['white'], '2026-09-01'),
        ],
    )

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json() == {'saved': 2}
    assert await _pending(client, ctx) == []
    student_id, enrollment_id = ctx['ana']
    belts = await client.get(
        f'/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts',
        headers=ctx['headers'],
    )
    assert belts.json()['current']['belt']['name'] == 'Amarela'
    assert belts.json()['current']['graduated_on'] == '2026-07-08'


@pytest.mark.asyncio
async def test_bulk_is_all_or_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    blue_jj = await create_belt(
        client, ctx['headers'], ctx['jiu_jitsu'], 'Azul'
    )

    response = await _bulk(
        client,
        ctx,
        [
            _item(ctx['ana'], ctx['yellow'], '2026-07-08'),
            _item(ctx['caio'], blue_jj, '2026-09-01'),
        ],
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'BELT_MODALITY_MISMATCH'
    assert len(await _pending(client, ctx)) == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_bulk_rejects_enrollment_of_other_modality(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    edu = await create_student(
        client, ctx['headers'], ctx['jiu_jitsu'], 'Edu Lima'
    )

    response = await _bulk(
        client, ctx, [_item(edu, ctx['white'], '2026-07-08')]
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'ENROLLMENT_MODALITY_MISMATCH'


@pytest.mark.asyncio
async def test_bulk_rejects_duplicate_enrollment(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await _bulk(
        client,
        ctx,
        [
            _item(ctx['ana'], ctx['white'], '2026-07-08'),
            _item(ctx['ana'], ctx['yellow'], '2026-08-08'),
        ],
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'DUPLICATE_ENROLLMENT_IN_BATCH'
    assert len(await _pending(client, ctx)) == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_bulk_empty_is_422(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await _bulk(client, ctx, [])

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.parametrize('student', ['bruno', 'duda'])
async def test_bulk_rejects_enrollment_not_pending(
    client: AsyncClient,
    db_session: AsyncSession,
    student: str,
) -> None:
    # Bruno já tem faixa; Duda está com a matrícula inativa
    ctx = await _setup(client, db_session)

    response = await _bulk(
        client,
        ctx,
        [
            _item(ctx['ana'], ctx['white'], '2026-07-08'),
            _item(ctx[student], ctx['yellow'], '2026-08-08'),
        ],
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'ENROLLMENT_NOT_PENDING'
    assert len(await _pending(client, ctx)) == 2  # noqa: PLR2004
