import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.master import Master
from tests.helpers.onboarding import register_web

EXPECTED_ACADEMY_COUNT = 2
EXPECTED_MASTER_COUNT = 2


@pytest.mark.asyncio
async def test_register_web_should_create_academy_and_master(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response, payload = await register_web(client)

    assert response.status_code == HTTPStatus.CREATED

    body = response.json()

    assert body['access_token']
    assert response.cookies['dojoflow_refresh']
    assert set(body) == {'access_token', 'token_type'}

    me_response = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {body["access_token"]}'},
    )

    assert me_response.status_code == HTTPStatus.OK
    me = me_response.json()

    assert me['email'] == payload['email']
    assert me['phone'] == payload['phone']
    assert me['academy']['name'] == payload['academy_name']
    assert set(me) == {
        'id',
        'name',
        'email',
        'phone',
        'academy',
        'support_mode',
    }
    assert set(me['academy']) == {'id', 'name', 'status'}
    uuid.UUID(me['id'])
    uuid.UUID(me['academy']['id'])

    master = (
        await db_session.execute(
            select(Master).where(Master.email == payload['email'])
        )
    ).scalar_one()

    assert master.password_hash is not None
    assert master.password_hash != payload['password']


@pytest.mark.asyncio
async def test_register_web_conflict_when_email_exists(
    client: AsyncClient,
) -> None:
    first_response, payload = await register_web(client)
    second_response, _ = await register_web(
        client,
        email=payload['email'],
        academy_name='Outra Academia',
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert second_response.status_code == HTTPStatus.CONFLICT
    assert second_response.json() == {
        'detail': 'This email is already registered as a master.',
        'code': 'EMAIL_ALREADY_REGISTERED',
    }


@pytest.mark.asyncio
async def test_login_and_me(
    client: AsyncClient,
) -> None:
    register_response, payload = await register_web(client)
    assert register_response.status_code == HTTPStatus.CREATED

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': payload['email'],
            'password': payload['password'],
        },
    )

    assert login_response.status_code == HTTPStatus.OK
    tokens = login_response.json()
    assert set(tokens) == {'access_token', 'token_type'}

    me_response = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {tokens["access_token"]}'},
    )

    assert me_response.status_code == HTTPStatus.OK
    me = me_response.json()

    assert me['email'] == payload['email']
    uuid.UUID(me['id'])
    assert 'master_id' not in me
    assert 'academy_id' not in me


@pytest.mark.asyncio
async def test_login_invalid_password(
    client: AsyncClient,
) -> None:
    _, payload = await register_web(client)

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': payload['email'],
            'password': 'senha-errada',
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'INVALID_CREDENTIALS'


@pytest.mark.asyncio
async def test_login_unknown_email_has_same_error_code(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/login',
        json={'email': 'ninguem@dojoflow.test', 'password': 'senha-segura'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'INVALID_CREDENTIALS'
