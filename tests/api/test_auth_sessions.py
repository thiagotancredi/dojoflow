from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.refresh_session import RefreshSession
from dojoflow.services.security import hash_refresh_token
from tests.helpers.onboarding import register_web

COOKIE = 'dojoflow_refresh'
REFRESH_URL = '/api/v1/auth/refresh'


def _use_cookie(client: AsyncClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(COOKIE, token)


@pytest.mark.asyncio
async def test_register_sets_httponly_cookie_and_hides_token(
    client: AsyncClient,
) -> None:
    response, _ = await register_web(client)

    assert 'refresh_token' not in response.json()
    set_cookie = response.headers['set-cookie']
    assert f'{COOKIE}=' in set_cookie
    assert 'HttpOnly' in set_cookie
    assert 'Path=/api/v1/auth' in set_cookie
    assert 'samesite=lax' in set_cookie.lower()


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient) -> None:
    register_response, _ = await register_web(client)
    first_token = register_response.cookies[COOKIE]

    _use_cookie(client, first_token)
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['access_token']
    assert response.cookies[COOKIE] != first_token


@pytest.mark.asyncio
async def test_refresh_without_cookie_is_unauthorized(
    client: AsyncClient,
) -> None:
    client.cookies.clear()

    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'REFRESH_TOKEN_INVALID'


@pytest.mark.asyncio
async def test_concurrent_tab_reuse_within_grace_keeps_session(
    client: AsyncClient,
) -> None:
    register_response, _ = await register_web(client)
    old_token = register_response.cookies[COOKIE]

    _use_cookie(client, old_token)
    first = await client.post(REFRESH_URL)
    _use_cookie(client, old_token)
    second = await client.post(REFRESH_URL)

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.OK

    _use_cookie(client, first.cookies[COOKIE])
    still_valid = await client.post(REFRESH_URL)

    assert still_valid.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_reuse_after_grace_revokes_every_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response, _ = await register_web(client)
    old_token = register_response.cookies[COOKIE]

    _use_cookie(client, old_token)
    rotated = await client.post(REFRESH_URL)
    new_token = rotated.cookies[COOKIE]

    await db_session.execute(
        update(RefreshSession)
        .where(RefreshSession.token_hash == hash_refresh_token(old_token))
        .values(revoked_at=datetime.now(UTC) - timedelta(minutes=5))
    )
    await db_session.commit()

    _use_cookie(client, old_token)
    reused = await client.post(REFRESH_URL)

    assert reused.status_code == HTTPStatus.UNAUTHORIZED
    assert reused.json()['code'] == 'REFRESH_TOKEN_REUSED'

    _use_cookie(client, new_token)
    after = await client.post(REFRESH_URL)

    assert after.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(
    client: AsyncClient,
) -> None:
    register_response, _ = await register_web(client)
    token = register_response.cookies[COOKIE]

    _use_cookie(client, token)
    logout = await client.post('/api/v1/auth/logout')

    assert logout.status_code == HTTPStatus.NO_CONTENT
    assert f'{COOKIE}=""' in logout.headers['set-cookie']

    _use_cookie(client, token)
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'REFRESH_TOKEN_INVALID'


@pytest.mark.asyncio
async def test_logout_without_cookie_is_noop(client: AsyncClient) -> None:
    client.cookies.clear()

    response = await client.post('/api/v1/auth/logout')

    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_grace_reuse_after_revoke_all_down_the_chain_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response, _ = await register_web(client)
    token_a = register_response.cookies[COOKIE]

    _use_cookie(client, token_a)
    first = await client.post(REFRESH_URL)
    _use_cookie(client, first.cookies[COOKIE])
    second = await client.post(REFRESH_URL)

    assert second.status_code == HTTPStatus.OK

    await db_session.execute(
        update(RefreshSession)
        .where(RefreshSession.replaced_by_id.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db_session.commit()

    _use_cookie(client, token_a)
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'REFRESH_TOKEN_INVALID'


@pytest.mark.asyncio
async def test_grace_reuse_with_revoked_successor_is_rejected(
    client: AsyncClient,
) -> None:
    register_response, _ = await register_web(client)
    old_token = register_response.cookies[COOKIE]

    _use_cookie(client, old_token)
    rotated = await client.post(REFRESH_URL)

    _use_cookie(client, rotated.cookies[COOKIE])
    await client.post('/api/v1/auth/logout')

    _use_cookie(client, old_token)
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'REFRESH_TOKEN_INVALID'


@pytest.mark.asyncio
async def test_expired_session_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response, _ = await register_web(client)
    token = register_response.cookies[COOKIE]

    await db_session.execute(
        update(RefreshSession)
        .where(RefreshSession.token_hash == hash_refresh_token(token))
        .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    await db_session.commit()

    _use_cookie(client, token)
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'REFRESH_TOKEN_INVALID'
