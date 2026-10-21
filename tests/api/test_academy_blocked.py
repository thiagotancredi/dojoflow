from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import SEED, auth_headers

LOGIN_URL = '/api/v1/auth/login'
REFRESH_URL = '/api/v1/auth/refresh'
ME_URL = '/api/v1/auth/me'
COOKIE = 'dojoflow_refresh'


async def _set_status(db_session: AsyncSession, status: str) -> None:
    await db_session.execute(
        text('UPDATE academy SET status = :status WHERE id = :id'),
        {'status': status, 'id': SEED.academy_id},
    )
    await db_session.commit()


async def _login(client: AsyncClient):
    return await client.post(
        LOGIN_URL,
        json={'email': SEED.email, 'password': SEED.password},
    )


@pytest.mark.asyncio
async def test_login_refused_when_academy_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _set_status(db_session, 'blocked')

    response = await _login(client)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'ACADEMY_BLOCKED'


@pytest.mark.asyncio
async def test_wrong_password_on_blocked_academy_does_not_reveal_status(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _set_status(db_session, 'blocked')

    response = await client.post(
        LOGIN_URL,
        json={'email': SEED.email, 'password': 'senha-errada'},
    )

    assert response.json()['code'] == 'INVALID_CREDENTIALS'


@pytest.mark.asyncio
async def test_refresh_refused_when_academy_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    login_response = await _login(client)
    assert login_response.status_code == HTTPStatus.OK
    await _set_status(db_session, 'blocked')

    client.cookies.clear()
    client.cookies.set(COOKIE, login_response.cookies[COOKIE])
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'ACADEMY_BLOCKED'


@pytest.mark.asyncio
async def test_authenticated_call_refused_when_academy_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    await _set_status(db_session, 'blocked')

    response = await client.get(ME_URL, headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'ACADEMY_BLOCKED'


@pytest.mark.asyncio
async def test_reactivated_academy_logs_in_again(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _set_status(db_session, 'blocked')
    assert (await _login(client)).status_code == HTTPStatus.UNAUTHORIZED

    await _set_status(db_session, 'active')

    assert (await _login(client)).status_code == HTTPStatus.OK
