import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, other_academy_headers
from tests.helpers.graduation import create_belt
from tests.helpers.scenario import add_belt, add_modality, add_student


def _url(student_id: str, enrollment_id: str) -> str:
    return f'/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts'


async def _setup(client: AsyncClient, db_session: AsyncSession) -> dict:
    # Montado direto no banco (os endpoints usados aqui têm testes próprios)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    white = await add_belt(
        db_session,
        taekwondo,
        'Branca',
        min_time_amount=3,
        min_time_unit='months',
    )
    yellow = await add_belt(
        db_session,
        taekwondo,
        'Amarela',
        primary_color='#facc15',
        min_time_amount=3,
        min_time_unit='months',
    )
    student_id, enrollment_id = await add_student(db_session, taekwondo)

    return {
        'headers': headers,
        'taekwondo': taekwondo,
        'white': white,
        'yellow': yellow,
        'url': _url(student_id, enrollment_id),
    }


async def _register(
    client: AsyncClient, ctx: dict, belt: dict, graduated_on: str
) -> None:
    response = await client.post(
        ctx['url'],
        headers=ctx['headers'],
        json={'belt_id': belt['id'], 'graduated_on': graduated_on},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.text


async def _read(client: AsyncClient, ctx: dict) -> dict:
    response = await client.get(ctx['url'], headers=ctx['headers'])
    assert response.status_code == HTTPStatus.OK, response.text

    return response.json()


@pytest.mark.asyncio
async def test_register_graduations_and_read_history(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    await _register(client, ctx, ctx['white'], '2020-01-10')
    await _register(client, ctx, ctx['yellow'], '2020-04-10')

    body = await _read(client, ctx)
    assert body['current']['belt']['name'] == 'Amarela'
    assert body['current']['graduated_on'] == '2020-04-10'
    assert body['eligibility'] == 'eligible'
    assert body['eligible_on'] == '2020-07-10'
    assert [item['belt']['name'] for item in body['history']] == [
        'Amarela',
        'Branca',
    ]
    uuid.UUID(body['history'][0]['id'])


@pytest.mark.asyncio
async def test_same_date_uses_last_created(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    await _register(client, ctx, ctx['white'], '2020-03-10')
    await _register(client, ctx, ctx['yellow'], '2020-03-10')

    body = await _read(client, ctx)
    assert body['current']['belt']['name'] == 'Amarela'


@pytest.mark.asyncio
async def test_no_belt_registered(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    body = await _read(client, ctx)

    assert body == {
        'current': None,
        'eligibility': 'no_belt',
        'eligible_on': None,
        'history': [],
    }


@pytest.mark.asyncio
async def test_belt_without_min_time(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    black = await add_belt(db_session, ctx['taekwondo'], 'Preta')

    await _register(client, ctx, black, '2020-01-01')

    body = await _read(client, ctx)
    assert body['eligibility'] == 'no_requirement'
    assert body['eligible_on'] is None


@pytest.mark.asyncio
async def test_belt_from_other_modality_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    jiu_jitsu = await add_modality(db_session, 'Jiu-jitsu')
    blue = await add_belt(db_session, jiu_jitsu, 'Azul')

    response = await client.post(
        ctx['url'],
        headers=ctx['headers'],
        json={'belt_id': blue['id'], 'graduated_on': '2020-01-01'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'BELT_MODALITY_MISMATCH'
    assert (await _read(client, ctx))['history'] == []


@pytest.mark.asyncio
async def test_belt_from_other_academy_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    other = await other_academy_headers(db_session)
    await client.put(
        f'/api/v1/academy/modalities/{ctx["taekwondo"]}/toggle',
        headers=other,
    )
    foreign = await create_belt(client, other, ctx['taekwondo'], 'Branca')

    response = await client.post(
        ctx['url'],
        headers=ctx['headers'],
        json={'belt_id': foreign['id'], 'graduated_on': '2020-01-01'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'BELT_NOT_FOUND'


@pytest.mark.asyncio
async def test_graduated_on_is_required(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)

    response = await client.post(
        ctx['url'],
        headers=ctx['headers'],
        json={'belt_id': ctx['white']['id']},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_edit_and_delete_record(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    await _register(client, ctx, ctx['white'], '2020-01-10')
    record_id = (await _read(client, ctx))['history'][0]['id']

    edited = await client.put(
        f'{ctx["url"]}/{record_id}',
        headers=ctx['headers'],
        json={'belt_id': ctx['yellow']['id'], 'graduated_on': '2021-05-05'},
    )

    assert edited.status_code == HTTPStatus.NO_CONTENT
    body = await _read(client, ctx)
    assert body['current']['id'] == record_id
    assert body['current']['belt']['name'] == 'Amarela'
    assert body['current']['graduated_on'] == '2021-05-05'

    deleted = await client.delete(
        f'{ctx["url"]}/{record_id}', headers=ctx['headers']
    )

    assert deleted.status_code == HTTPStatus.NO_CONTENT
    assert (await _read(client, ctx))['history'] == []

    again = await client.delete(
        f'{ctx["url"]}/{record_id}', headers=ctx['headers']
    )

    assert again.status_code == HTTPStatus.NOT_FOUND
    assert again.json()['code'] == 'BELT_RECORD_NOT_FOUND'


@pytest.mark.asyncio
async def test_belt_in_history_cannot_be_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    ctx = await _setup(client, db_session)
    await _register(client, ctx, ctx['white'], '2020-01-10')

    response = await client.delete(
        f'/api/v1/academy/belts/{ctx["white"]["id"]}',
        headers=ctx['headers'],
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'BELT_IN_USE'


@pytest.mark.asyncio
@pytest.mark.parametrize('graduated_on', ['9999-12-01', '1800-01-01'])
async def test_graduated_on_out_of_range_is_422(
    client: AsyncClient,
    db_session: AsyncSession,
    graduated_on: str,
) -> None:
    ctx = await _setup(client, db_session)

    response = await client.post(
        ctx['url'],
        headers=ctx['headers'],
        json={'belt_id': ctx['white']['id'], 'graduated_on': graduated_on},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
