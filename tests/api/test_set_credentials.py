from http import HTTPStatus

import pytest
from httpx import AsyncClient

from tests.helpers.onboarding import register_web

URL = '/api/v1/auth/set-credentials'
COOKIE = 'dojoflow_refresh'


async def _login(client: AsyncClient) -> tuple[dict[str, str], str]:
    response, _ = await register_web(client)
    token = response.json()['access_token']

    return {'Authorization': f'Bearer {token}'}, response.cookies[COOKIE]


@pytest.mark.asyncio
async def test_authenticated_without_current_password_is_forbidden(
    client: AsyncClient,
) -> None:
    headers, _ = await _login(client)

    response = await client.post(
        URL,
        headers=headers,
        json={'email': 'novo@dojoflow.test', 'password': 'nova-senha-123'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['code'] == 'CURRENT_PASSWORD_INVALID'


@pytest.mark.asyncio
async def test_authenticated_with_wrong_current_password_is_forbidden(
    client: AsyncClient,
) -> None:
    headers, _ = await _login(client)

    response = await client.post(
        URL,
        headers=headers,
        json={
            'email': 'novo@dojoflow.test',
            'password': 'nova-senha-123',
            'current_password': 'senha-errada',
        },
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_password_change_revokes_old_sessions(
    client: AsyncClient,
) -> None:
    headers, old_refresh = await _login(client)

    response = await client.post(
        URL,
        headers=headers,
        json={
            'email': 'mestre@dojoflow.test',
            'password': 'nova-senha-123',
            'current_password': 'senha-segura',
        },
    )

    assert response.status_code == HTTPStatus.OK
    new_refresh = response.cookies[COOKIE]

    client.cookies.clear()
    client.cookies.set(COOKIE, old_refresh)
    old_attempt = await client.post('/api/v1/auth/refresh')

    client.cookies.clear()
    client.cookies.set(COOKIE, new_refresh)
    new_attempt = await client.post('/api/v1/auth/refresh')

    assert old_attempt.status_code == HTTPStatus.UNAUTHORIZED
    assert new_attempt.status_code == HTTPStatus.OK


async def _setup_token(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post(
        '/api/v1/auth/telegram/setup-token', headers=headers
    )

    return response.json()['token']


@pytest.mark.asyncio
async def test_setup_token_survives_email_conflict(
    client: AsyncClient,
) -> None:
    await register_web(client, email='ocupado@dojoflow.test')
    response, _ = await register_web(
        client, email='base@dojoflow.test', academy_name='Outra Academia'
    )
    headers = {'Authorization': f'Bearer {response.json()["access_token"]}'}
    token = await _setup_token(client, headers)

    conflict = await client.post(
        URL,
        json={
            'email': 'ocupado@dojoflow.test',
            'password': 'nova-senha-123',
            'setup_token': token,
        },
    )
    retry = await client.post(
        URL,
        json={
            'email': 'livre@dojoflow.test',
            'password': 'nova-senha-123',
            'setup_token': token,
        },
    )

    assert conflict.status_code == HTTPStatus.CONFLICT
    assert conflict.json()['code'] == 'EMAIL_ALREADY_REGISTERED'
    assert retry.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_setup_token_takes_precedence_over_bearer(
    client: AsyncClient,
) -> None:
    headers, _ = await _login(client)
    token = await _setup_token(client, headers)

    response = await client.post(
        URL,
        headers=headers,
        json={
            'email': 'novo@dojoflow.test',
            'password': 'nova-senha-123',
            'setup_token': token,
        },
    )

    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_setup_token_ignores_invalid_bearer(
    client: AsyncClient,
) -> None:
    headers, _ = await _login(client)
    token = await _setup_token(client, headers)

    response = await client.post(
        URL,
        headers={'Authorization': 'Bearer token-invalido'},
        json={
            'email': 'novo@dojoflow.test',
            'password': 'nova-senha-123',
            'setup_token': token,
        },
    )

    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_setup_token_works_only_once(client: AsyncClient) -> None:
    headers, _ = await _login(client)
    token = await _setup_token(client, headers)
    payload = {
        'email': 'novo@dojoflow.test',
        'password': 'nova-senha-123',
        'setup_token': token,
    }

    first = await client.post(URL, json=payload)
    second = await client.post(URL, json=payload)

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.UNAUTHORIZED
    assert second.json()['code'] == 'SETUP_TOKEN_INVALID'


@pytest.mark.asyncio
async def test_setup_path_needs_no_current_password_and_revokes_sessions(
    client: AsyncClient,
) -> None:
    headers, old_refresh = await _login(client)
    token = await _setup_token(client, headers)
    client.cookies.clear()

    response = await client.post(
        URL,
        json={
            'email': 'novo@dojoflow.test',
            'password': 'nova-senha-123',
            'setup_token': token,
        },
    )

    assert response.status_code == HTTPStatus.OK

    client.cookies.clear()
    client.cookies.set(COOKIE, old_refresh)
    old_attempt = await client.post('/api/v1/auth/refresh')

    assert old_attempt.status_code == HTTPStatus.UNAUTHORIZED
