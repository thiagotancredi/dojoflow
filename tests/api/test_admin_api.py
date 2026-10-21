from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from tests.helpers.auth import SEED, auth_headers, other_academy_headers

ADMIN_URL = '/api/v1/admin'
ACADEMIES_URL = f'{ADMIN_URL}/academies'
NEW_ACADEMY = {
    'academy_name': 'Dojo Novo',
    'master_name': 'Mestre Novo',
    'email': '  Novo@Dojo.TEST ',
    'phone': '62988887777',
}


async def _create(
    client: AsyncClient,
    headers: dict[str, str],
    **overrides: object,
):
    return await client.post(
        ACADEMIES_URL,
        headers=headers,
        json={**NEW_ACADEMY, **overrides},
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures('_admin_is_seed')
@pytest.mark.parametrize(
    ('method', 'url'),
    [
        ('GET', f'{ADMIN_URL}/me'),
        ('GET', ACADEMIES_URL),
        ('POST', ACADEMIES_URL),
    ],
)
async def test_non_admin_gets_403(
    client: AsyncClient,
    db_session: AsyncSession,
    method: str,
    url: str,
) -> None:
    headers = await other_academy_headers(db_session)

    response = await client.request(
        method, url, headers=headers, json=NEW_ACADEMY
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['code'] == 'ADMIN_ONLY'


@pytest.mark.asyncio
async def test_no_admin_when_admin_email_empty(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, 'ADMIN_EMAIL', '')

    response = await client.get(
        f'{ADMIN_URL}/me', headers=await auth_headers(client)
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_admin_me_returns_context(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(f'{ADMIN_URL}/me', headers=admin_headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['email'] == SEED.email


@pytest.mark.asyncio
async def test_unauthenticated_admin_call_is_401(client: AsyncClient) -> None:
    response = await client.get(ACADEMIES_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_academy_returns_password_and_master_can_log_in(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await _create(client, admin_headers)

    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    password_length = 12
    assert len(body['password']) == password_length
    assert body['academy']['name'] == 'Dojo Novo'
    assert body['academy']['status'] == 'active'
    assert body['academy']['is_own'] is False
    assert body['academy']['master']['email'] == 'novo@dojo.test'
    assert body['academy']['master']['phone'] == '62988887777'

    login = await client.post(
        '/api/v1/auth/login',
        json={'email': 'novo@dojo.test', 'password': body['password']},
    )
    assert login.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_create_academy_duplicate_email_conflict(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await _create(client, admin_headers, email=SEED.email.upper())

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'EMAIL_ALREADY_REGISTERED'


@pytest.mark.asyncio
async def test_create_academy_rejects_short_names(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await _create(client, admin_headers, academy_name='A')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_list_academies_search_and_is_own(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    await _create(
        client,
        admin_headers,
        academy_name='Dojo Tigre',
        master_name='Carlos Souza',
        email='carlos@tigre.test',
    )
    await _create(client, admin_headers, email='outra@dojo.test')

    everything = await client.get(ACADEMIES_URL, headers=admin_headers)
    by_master = await client.get(
        ACADEMIES_URL, headers=admin_headers, params={'search': 'carl'}
    )
    by_academy = await client.get(
        ACADEMIES_URL, headers=admin_headers, params={'search': 'TIGRE'}
    )

    rows = everything.json()
    expected_total = 3
    assert len(rows) == expected_total
    own = [row for row in rows if row['is_own']]
    assert [row['name'] for row in own] == [SEED.academy_name]
    assert [row['name'] for row in by_master.json()] == ['Dojo Tigre']
    assert [row['name'] for row in by_academy.json()] == ['Dojo Tigre']


async def _other_academy(client: AsyncClient, headers: dict[str, str]):
    created = await _create(client, headers, email='mestre@outra.test')
    body = created.json()

    return body['academy'], body['password']


async def _own_academy_id(client: AsyncClient, headers: dict[str, str]) -> str:
    rows = (await client.get(ACADEMIES_URL, headers=headers)).json()

    return next(row['id'] for row in rows if row['is_own'])


async def _login_cookie(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        '/api/v1/auth/login', json={'email': email, 'password': password}
    )
    assert response.status_code == HTTPStatus.OK

    return response.cookies['dojoflow_refresh']


async def _refresh_with(client: AsyncClient, cookie: str):
    client.cookies.clear()
    client.cookies.set('dojoflow_refresh', cookie)
    response = await client.post('/api/v1/auth/refresh')
    client.cookies.clear()

    return response


@pytest.mark.asyncio
async def test_update_academy_and_master(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    academy, _ = await _other_academy(client, admin_headers)

    response = await client.patch(
        f'{ACADEMIES_URL}/{academy["id"]}',
        headers=admin_headers,
        json={
            'academy_name': 'Novo Nome',
            'master_name': 'Mestre Renomeado',
            'email': ' X@Y.TEST ',
            'phone': None,
        },
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['name'] == 'Novo Nome'
    assert body['master']['name'] == 'Mestre Renomeado'
    assert body['master']['email'] == 'x@y.test'
    assert body['master']['phone'] is None


@pytest.mark.asyncio
async def test_update_keeps_omitted_fields(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    academy, _ = await _other_academy(client, admin_headers)

    response = await client.patch(
        f'{ACADEMIES_URL}/{academy["id"]}',
        headers=admin_headers,
        json={'academy_name': 'Só o Nome'},
    )

    master = response.json()['master']
    assert master['email'] == 'mestre@outra.test'
    assert master['phone'] == NEW_ACADEMY['phone']


@pytest.mark.asyncio
async def test_update_email_conflict(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    academy, _ = await _other_academy(client, admin_headers)

    response = await client.patch(
        f'{ACADEMIES_URL}/{academy["id"]}',
        headers=admin_headers,
        json={'email': SEED.email},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'EMAIL_ALREADY_REGISTERED'


@pytest.mark.asyncio
async def test_update_same_email_is_not_a_conflict(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    academy, _ = await _other_academy(client, admin_headers)

    response = await client.patch(
        f'{ACADEMIES_URL}/{academy["id"]}',
        headers=admin_headers,
        json={'email': 'MESTRE@outra.test'},
    )

    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_admin_cannot_change_own_email(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    own_id = await _own_academy_id(client, admin_headers)

    response = await client.patch(
        f'{ACADEMIES_URL}/{own_id}',
        headers=admin_headers,
        json={'email': 'outro@x.test'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'ADMIN_EMAIL_LOCKED'


@pytest.mark.asyncio
async def test_admin_can_rename_own_academy(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    own_id = await _own_academy_id(client, admin_headers)

    response = await client.patch(
        f'{ACADEMIES_URL}/{own_id}',
        headers=admin_headers,
        json={'academy_name': 'Katsuflow', 'email': SEED.email},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['name'] == 'Katsuflow'


@pytest.mark.asyncio
async def test_reset_password_revokes_sessions(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    academy, old_password = await _other_academy(client, admin_headers)
    email = academy['master']['email']
    cookie = await _login_cookie(client, email, old_password)

    response = await client.post(
        f'{ACADEMIES_URL}/{academy["id"]}/reset-password',
        headers=admin_headers,
    )

    assert response.status_code == HTTPStatus.OK
    new_password = response.json()['password']
    assert new_password != old_password
    refreshed = await _refresh_with(client, cookie)
    assert refreshed.status_code == HTTPStatus.UNAUTHORIZED
    old_login = await client.post(
        '/api/v1/auth/login', json={'email': email, 'password': old_password}
    )
    assert old_login.status_code == HTTPStatus.UNAUTHORIZED
    assert await _login_cookie(client, email, new_password)


@pytest.mark.asyncio
async def test_block_logs_out_and_unblock_restores(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    academy, password = await _other_academy(client, admin_headers)
    email = academy['master']['email']
    cookie = await _login_cookie(client, email, password)
    status_url = f'{ACADEMIES_URL}/{academy["id"]}/status'

    blocked = await client.post(
        status_url, headers=admin_headers, json={'status': 'blocked'}
    )

    assert blocked.status_code == HTTPStatus.OK
    assert blocked.json()['status'] == 'blocked'
    assert (await _refresh_with(client, cookie)).status_code == (
        HTTPStatus.UNAUTHORIZED
    )
    login = await client.post(
        '/api/v1/auth/login', json={'email': email, 'password': password}
    )
    assert login.json()['code'] == 'ACADEMY_BLOCKED'

    unblocked = await client.post(
        status_url, headers=admin_headers, json={'status': 'active'}
    )

    assert unblocked.json()['status'] == 'active'
    assert await _login_cookie(client, email, password)


@pytest.mark.asyncio
async def test_cannot_block_own_academy(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    own_id = await _own_academy_id(client, admin_headers)

    response = await client.post(
        f'{ACADEMIES_URL}/{own_id}/status',
        headers=admin_headers,
        json={'status': 'blocked'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'CANNOT_BLOCK_OWN_ACADEMY'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('method', 'suffix', 'body'),
    [
        ('PATCH', '', {'academy_name': 'Nome'}),
        ('POST', '/reset-password', None),
        ('POST', '/status', {'status': 'blocked'}),
    ],
)
async def test_unknown_academy_404(
    client: AsyncClient,
    admin_headers: dict[str, str],
    method: str,
    suffix: str,
    body: dict[str, str] | None,
) -> None:
    url = f'{ACADEMIES_URL}/00000000-0000-0000-0000-000000000000{suffix}'

    response = await client.request(
        method, url, headers=admin_headers, json=body
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'ACADEMY_NOT_FOUND'


@pytest.mark.asyncio
async def test_non_admin_gets_403_before_academy_lookup(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, 'ADMIN_EMAIL', SEED.email)
    headers = await other_academy_headers(db_session)
    url = f'{ACADEMIES_URL}/00000000-0000-0000-0000-000000000000/status'

    response = await client.post(
        url, headers=headers, json={'status': 'blocked'}
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['code'] == 'ADMIN_ONLY'
