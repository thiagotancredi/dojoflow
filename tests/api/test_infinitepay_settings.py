from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.crypto import decrypt_secret
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from tests.helpers.auth import SEED, auth_headers, other_academy_headers
from tests.helpers.infinitepay import (
    checkout_disabled,
    fake_infinitepay,
    key_rejected,
    unreachable,
)

URL = '/api/v1/academy/infinitepay'
API_KEY = 'inchk_live_SUPERSECRETkey9876'
CONNECT = {'handle': 'katsuflow', 'api_key': API_KEY}


async def _settings(session: AsyncSession) -> AcademyBillingSettings | None:
    session.expire_all()
    return await session.scalar(
        select(AcademyBillingSettings).where(
            AcademyBillingSettings.academy_id == SEED.academy_id
        )
    )


@pytest.mark.asyncio
async def test_status_when_never_connected(client: AsyncClient):
    headers = await auth_headers(client)

    response = await client.get(URL, headers=headers)

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json() == {
        'enabled': False,
        'handle': None,
        'tested_at': None,
        'key_last4': None,
    }


@pytest.mark.asyncio
async def test_connect_success_enables(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)

    with fake_infinitepay() as fake:
        response = await client.put(URL, headers=headers, json=CONNECT)

    assert response.status_code == HTTPStatus.OK, response.text
    body = response.json()
    assert body['enabled'] is True
    assert body['handle'] == 'katsuflow'
    assert body['tested_at'] is not None
    assert body['key_last4'] == '9876'

    # Link de teste: R$ 1,00, sem aviso, com a chave no header
    [request] = fake.requests
    assert request.url.path == '/links'
    assert request.headers['X-Api-Key'] == API_KEY
    [link] = fake.bodies('/links')
    assert link['order_nsu'].startswith('kftest-')
    assert link['items'] == [
        {
            'description': 'Teste de conexão Katsuflow',
            'quantity': 1,
            'price': 100,
        }
    ]
    assert 'webhook_url' not in link

    saved = await _settings(db_session)
    assert saved.infinitepay_enabled is True
    assert API_KEY not in saved.infinitepay_api_key
    assert decrypt_secret(saved.infinitepay_api_key) == API_KEY


@pytest.mark.asyncio
async def test_connect_keeps_pix_settings(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    await client.put(
        '/api/v1/academy/billing-settings',
        headers=headers,
        json={'pix_key': 'dojo@exemplo.com', 'pix_key_type': 'email'},
    )

    with fake_infinitepay():
        await client.put(URL, headers=headers, json=CONNECT)

    pix = await client.get('/api/v1/academy/billing-settings', headers=headers)
    assert pix.json()['pix_key'] == 'dojo@exemplo.com'


@pytest.mark.asyncio
async def test_connect_normalizes_handle(client: AsyncClient):
    headers = await auth_headers(client)

    with fake_infinitepay():
        response = await client.put(
            URL,
            headers=headers,
            json={'handle': ' $KatsuFlow ', 'api_key': f' {API_KEY} '},
        )

    assert response.json()['handle'] == 'katsuflow'


@pytest.mark.asyncio
async def test_connect_requires_handle_and_key(client: AsyncClient):
    headers = await auth_headers(client)

    with fake_infinitepay() as fake:
        response = await client.put(
            URL, headers=headers, json={'handle': ' $ ', 'api_key': ' '}
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert fake.requests == []


@pytest.mark.asyncio
async def test_connect_key_rejected_does_not_enable(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)

    with fake_infinitepay(key_rejected()):
        response = await client.put(URL, headers=headers, json=CONNECT)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'code': 'INFINITEPAY_KEY_REJECTED',
        'detail': (
            'A chave de API não foi aceita. Crie uma chave nova no app da '
            'InfinitePay (Checkout → Configurações → API Keys) e cole aqui.'
        ),
    }
    saved = await _settings(db_session)
    assert saved is None or saved.infinitepay_enabled is False
    assert (await client.get(URL, headers=headers)).json()['enabled'] is False


@pytest.mark.asyncio
async def test_connect_checkout_disabled_message(client: AsyncClient):
    headers = await auth_headers(client)

    with fake_infinitepay(checkout_disabled()):
        response = await client.put(URL, headers=headers, json=CONNECT)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'code': 'INFINITEPAY_CHECKOUT_DISABLED',
        'detail': (
            'A InfinitePay ainda não liberou o checkout para essa tag. '
            'Confira se a tag está certa e, no app da InfinitePay, desligue '
            "e ligue de novo 'Habilitar Checkout Integrado'."
        ),
    }


@pytest.mark.asyncio
async def test_connect_unavailable_message(client: AsyncClient):
    headers = await auth_headers(client)

    with fake_infinitepay(unreachable()):
        response = await client.put(URL, headers=headers, json=CONNECT)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'code': 'INFINITEPAY_UNAVAILABLE',
        'detail': (
            'Não foi possível falar com a InfinitePay agora. Tente de novo.'
        ),
    }


@pytest.mark.asyncio
async def test_failed_key_change_keeps_working_connection(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    with fake_infinitepay():
        await client.put(URL, headers=headers, json=CONNECT)

    with fake_infinitepay(key_rejected()):
        await client.put(
            URL,
            headers=headers,
            json={'handle': 'katsuflow', 'api_key': 'inchk_wrong_0000'},
        )

    status = (await client.get(URL, headers=headers)).json()
    assert status['enabled'] is True
    assert status['key_last4'] == '9876'


@pytest.mark.asyncio
async def test_settings_never_return_api_key(client: AsyncClient):
    headers = await auth_headers(client)

    with fake_infinitepay():
        connected = await client.put(URL, headers=headers, json=CONNECT)
    read = await client.get(URL, headers=headers)
    pix = await client.get('/api/v1/academy/billing-settings', headers=headers)

    for response in (connected, read, pix):
        assert API_KEY not in response.text
        assert 'SUPERSECRET' not in response.text


@pytest.mark.asyncio
async def test_disconnect_keeps_handle(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    with fake_infinitepay():
        await client.put(URL, headers=headers, json=CONNECT)

    response = await client.delete(URL, headers=headers)

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['enabled'] is False
    assert response.json()['handle'] == 'katsuflow'
    saved = await _settings(db_session)
    assert decrypt_secret(saved.infinitepay_api_key) == API_KEY


@pytest.mark.asyncio
async def test_infinitepay_settings_isolated_by_academy(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    other = await other_academy_headers(db_session)
    with fake_infinitepay():
        await client.put(URL, headers=headers, json=CONNECT)

    other_status = (await client.get(URL, headers=other)).json()
    await client.delete(URL, headers=other)

    assert other_status['enabled'] is False
    assert other_status['handle'] is None
    assert (await client.get(URL, headers=headers)).json()['enabled'] is True


@pytest.mark.asyncio
async def test_infinitepay_settings_require_login(client: AsyncClient):
    response = await client.get(URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_connect_sends_handle_in_test_link(client: AsyncClient):
    # A tag vai no link de teste: a InfinitePay recusa tag inexistente
    headers = await auth_headers(client)

    with fake_infinitepay() as fake:
        await client.put(
            URL, headers=headers, json={**CONNECT, 'handle': '$KatsuFlow'}
        )

    assert fake.bodies('/links')[0]['handle'] == 'katsuflow'
