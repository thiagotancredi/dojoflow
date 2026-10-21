from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.models.academy import Academy
from dojoflow.models.audit_log import AuditLog
from dojoflow.models.one_time_token import OneTimeToken
from dojoflow.models.refresh_session import RefreshSession
from dojoflow.services.security import hash_refresh_token
from tests.helpers.auth import SEED, other_academy_headers
from tests.helpers.scenario import add_modality, add_student

COOKIE = 'dojoflow_refresh'
EXCHANGE_URL = '/api/v1/auth/support/exchange'
ACADEMIES_URL = '/api/v1/admin/academies'
SUPPORT_HOURS = 8


async def _other_academy(db_session: AsyncSession) -> Academy:
    await other_academy_headers(db_session)
    academy = await db_session.scalar(
        select(Academy).where(Academy.name == 'Outra Academia')
    )
    assert academy is not None

    return academy


async def _entry_code(
    client: AsyncClient,
    admin_headers: dict[str, str],
    academy: Academy,
) -> str:
    response = await client.post(
        f'{ACADEMIES_URL}/{academy.public_id}/support-entry',
        headers=admin_headers,
    )
    assert response.status_code == HTTPStatus.OK

    return response.json()['code']


async def _enter(
    client: AsyncClient,
    admin_headers: dict[str, str],
    academy: Academy,
) -> tuple[dict[str, str], str]:
    code = await _entry_code(client, admin_headers, academy)
    response = await client.post(EXCHANGE_URL, json={'code': code})
    assert response.status_code == HTTPStatus.OK
    cookie = response.cookies[COOKIE]
    client.cookies.clear()
    token = response.json()['access_token']

    return {'Authorization': f'Bearer {token}'}, cookie


async def _refresh(client: AsyncClient, cookie: str):
    client.cookies.clear()
    client.cookies.set(COOKIE, cookie)
    response = await client.post('/api/v1/auth/refresh')
    client.cookies.clear()

    return response


@pytest.mark.asyncio
async def test_support_flow_sees_target_academy(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    judo = await add_modality(db_session, 'Judô', academy_id=academy.id)
    await add_student(
        db_session, judo, 'Aluno da Outra', academy_id=academy.id
    )
    seed_judo = await add_modality(db_session, 'Jiu-Jitsu')
    await add_student(db_session, seed_judo, 'Aluno do Seed')

    headers, _ = await _enter(client, admin_headers, academy)

    me = await client.get('/api/v1/auth/me', headers=headers)
    assert me.status_code == HTTPStatus.OK
    assert me.json()['academy']['name'] == 'Outra Academia'
    assert me.json()['support_mode'] is True
    assert me.json()['email'] == SEED.email
    students = await client.get('/api/v1/students', headers=headers)
    names = [item['name'] for item in students.json()['items']]
    assert names == ['Aluno da Outra']


@pytest.mark.asyncio
async def test_normal_session_is_not_support_mode(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    me = await client.get('/api/v1/auth/me', headers=admin_headers)

    assert me.json()['support_mode'] is False


@pytest.mark.asyncio
async def test_support_code_single_use(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    code = await _entry_code(client, admin_headers, academy)

    first = await client.post(EXCHANGE_URL, json={'code': code})
    client.cookies.clear()
    second = await client.post(EXCHANGE_URL, json={'code': code})

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.UNAUTHORIZED
    assert second.json()['code'] == 'SUPPORT_CODE_INVALID'


@pytest.mark.asyncio
async def test_support_code_expires(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    code = await _entry_code(client, admin_headers, academy)
    await db_session.execute(
        update(OneTimeToken)
        .where(OneTimeToken.token == code)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db_session.commit()

    response = await client.post(EXCHANGE_URL, json={'code': code})

    assert response.json()['code'] == 'SUPPORT_CODE_INVALID'


@pytest.mark.asyncio
async def test_support_code_lives_60_seconds(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    code = await _entry_code(client, admin_headers, academy)

    token = await db_session.scalar(
        select(OneTimeToken).where(OneTimeToken.token == code)
    )

    assert token is not None
    lifetime = token.expires_at - datetime.now(UTC)
    assert timedelta(seconds=50) < lifetime <= timedelta(seconds=60)
    assert token.academy_id == academy.id


@pytest.mark.asyncio
async def test_setup_token_is_not_a_support_code(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    db_session.add(
        OneTimeToken(
            master_id=SEED.master_id,
            token='setup-token-de-telegram',
            purpose='telegram_setup',
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )
    await db_session.commit()

    response = await client.post(
        EXCHANGE_URL, json={'code': 'setup-token-de-telegram'}
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'SUPPORT_CODE_INVALID'


@pytest.mark.asyncio
async def test_support_refresh_keeps_academy_and_deadline(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    _, cookie = await _enter(client, admin_headers, academy)
    original = await db_session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(cookie)
        )
    )
    assert original is not None
    session_length = original.expires_at - datetime.now(UTC)
    assert timedelta(hours=SUPPORT_HOURS - 1) < session_length
    assert session_length <= timedelta(hours=SUPPORT_HOURS)

    refreshed = await _refresh(client, cookie)

    assert refreshed.status_code == HTTPStatus.OK
    new_cookie = refreshed.cookies[COOKIE]
    rotated = await db_session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(new_cookie)
        )
    )
    assert rotated is not None
    assert rotated.acting_academy_id == academy.id
    assert rotated.expires_at == original.expires_at
    me = await client.get(
        '/api/v1/auth/me',
        headers={
            'Authorization': f'Bearer {refreshed.json()["access_token"]}'
        },
    )
    assert me.json()['academy']['name'] == 'Outra Academia'


@pytest.mark.asyncio
async def test_support_session_ends_after_deadline(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    _, cookie = await _enter(client, admin_headers, academy)
    await db_session.execute(
        update(RefreshSession)
        .where(RefreshSession.token_hash == hash_refresh_token(cookie))
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db_session.commit()

    response = await _refresh(client, cookie)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_support_refused_when_admin_email_changes(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    academy = await _other_academy(db_session)
    headers, _ = await _enter(client, admin_headers, academy)

    monkeypatch.setattr(settings, 'ADMIN_EMAIL', 'outro@x.test')
    response = await client.get('/api/v1/auth/me', headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'SUPPORT_SESSION_INVALID'


@pytest.mark.asyncio
async def test_support_works_on_blocked_academy(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    await db_session.execute(
        text("UPDATE academy SET status = 'blocked' WHERE id = :id"),
        {'id': academy.id},
    )
    await db_session.commit()

    headers, cookie = await _enter(client, admin_headers, academy)

    me = await client.get('/api/v1/auth/me', headers=headers)
    assert me.status_code == HTTPStatus.OK
    assert me.json()['academy']['status'] == 'blocked'
    assert (await _refresh(client, cookie)).status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('url', 'code'),
    [
        ('/api/v1/auth/set-credentials', 'SUPPORT_MODE'),
        ('/api/v1/auth/telegram/link-token', 'SUPPORT_MODE'),
        ('/api/v1/auth/telegram/setup-token', 'SUPPORT_MODE'),
        (ACADEMIES_URL, 'ADMIN_ONLY'),
    ],
)
async def test_account_and_admin_routes_refused_in_support(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
    url: str,
    code: str,
) -> None:
    academy = await _other_academy(db_session)
    headers, _ = await _enter(client, admin_headers, academy)

    response = await client.post(
        url,
        headers=headers,
        json={
            'email': 'novo@x.test',
            'password': 'senha-nova-123',
            'current_password': SEED.password,
            'academy_name': 'X Y',
            'master_name': 'X Y',
        },
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['code'] == code


@pytest.mark.asyncio
@pytest.mark.usefixtures('_admin_is_seed')
async def test_non_admin_cannot_create_support_entry(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await other_academy_headers(db_session)
    academy = await db_session.scalar(
        select(Academy).where(Academy.id == SEED.academy_id)
    )
    assert academy is not None

    response = await client.post(
        f'{ACADEMIES_URL}/{academy.public_id}/support-entry', headers=headers
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_support_entry_writes_audit_log(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)

    await _entry_code(client, admin_headers, academy)

    rows = (await db_session.scalars(select(AuditLog))).all()
    assert len(rows) == 1
    assert rows[0].action.value == 'support_entry'
    assert rows[0].entity_name == 'academy'
    assert rows[0].entity_id == academy.id
    assert rows[0].master_id == SEED.master_id
    assert rows[0].academy_id == academy.id


@pytest.mark.asyncio
async def test_logout_ends_support_session(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    academy = await _other_academy(db_session)
    _, cookie = await _enter(client, admin_headers, academy)

    client.cookies.set(COOKIE, cookie)
    await client.post('/api/v1/auth/logout')

    assert (await _refresh(client, cookie)).status_code == (
        HTTPStatus.UNAUTHORIZED
    )


@pytest.mark.asyncio
async def test_support_refresh_reuse_within_grace_keeps_academy(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    # Duas abas renovando com o mesmo cookie ao mesmo tempo
    academy = await _other_academy(db_session)
    _, cookie = await _enter(client, admin_headers, academy)

    first = await _refresh(client, cookie)
    second = await _refresh(client, cookie)

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.OK
    me = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {second.json()["access_token"]}'},
    )
    assert me.json()['academy']['name'] == 'Outra Academia'
    assert me.json()['support_mode'] is True
