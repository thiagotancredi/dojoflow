from http import HTTPStatus

import pytest
import pytest_asyncio
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


@pytest.fixture
def _admin_is_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, 'ADMIN_EMAIL', SEED.email)


@pytest_asyncio.fixture
async def admin_headers(
    client: AsyncClient,
    _admin_is_seed: None,
) -> dict[str, str]:
    return await auth_headers(client)


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
