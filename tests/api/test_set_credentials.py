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


@pytest.mark.asyncio
async def test_set_credentials_requires_login(client: AsyncClient) -> None:
    response = await client.post(
        URL,
        json={'email': 'novo@dojoflow.test', 'password': 'nova-senha-123'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
