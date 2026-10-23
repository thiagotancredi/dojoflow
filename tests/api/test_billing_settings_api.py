from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.services.billing import DEFAULT_MESSAGE_TEMPLATE
from tests.helpers.auth import auth_headers, other_academy_headers

URL = '/api/v1/academy/billing-settings'

SETTINGS = {
    'pix_key': 'dojo@exemplo.com',
    'pix_key_type': 'email',
    'pix_city': 'Goiânia',
    'recipient_name': 'Dojo Dragão Branco',
    'bank_details': 'Banco 001 · Agência 1234 · Conta 5678-9',
    'message_template': 'Oi, {nome}! Falta {valor} ({meses}).',
}


@pytest.mark.asyncio
async def test_settings_default_template(client: AsyncClient):
    headers = await auth_headers(client)

    response = await client.get(URL, headers=headers)

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json() == {
        'pix_key': None,
        'pix_key_type': None,
        'pix_city': None,
        'recipient_name': None,
        'bank_details': None,
        'message_template': DEFAULT_MESSAGE_TEMPLATE,
    }
    assert DEFAULT_MESSAGE_TEMPLATE == (
        'Olá, {nome}! Tudo bem? 🥋\n\n'
        'Passando para lembrar que a mensalidade da {academia} está em '
        'aberto: {valor} ({meses}).\n\n'
        'Para pagar pelo Pix, é só tocar aqui:\n{link}\n\n'
        'Se já pagou, desconsidere. Obrigado!'
    )


@pytest.mark.asyncio
async def test_settings_roundtrip(client: AsyncClient):
    headers = await auth_headers(client)

    saved = await client.put(URL, headers=headers, json=SETTINGS)
    read = await client.get(URL, headers=headers)

    assert saved.status_code == HTTPStatus.OK, saved.text
    assert saved.json() == SETTINGS
    assert read.json() == SETTINGS

    # Salvar de novo substitui; texto vazio volta ao padrão
    cleared = await client.put(
        URL,
        headers=headers,
        json={**SETTINGS, 'bank_details': '  ', 'message_template': ''},
    )
    assert cleared.json()['bank_details'] is None
    assert cleared.json()['message_template'] == DEFAULT_MESSAGE_TEMPLATE


@pytest.mark.asyncio
async def test_settings_rejects_too_long_values(client: AsyncClient):
    headers = await auth_headers(client)

    response = await client.put(
        URL, headers=headers, json={**SETTINGS, 'pix_key': 'x' * 141}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_settings_scoped_to_academy(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    await client.put(URL, headers=headers, json=SETTINGS)
    other_headers = await other_academy_headers(db_session)

    response = await client.get(URL, headers=other_headers)

    assert response.json()['pix_key'] is None
    assert response.json()['message_template'] == DEFAULT_MESSAGE_TEMPLATE


@pytest.mark.asyncio
async def test_settings_requires_key_type(client: AsyncClient):
    headers = await auth_headers(client)

    response = await client.put(
        URL, headers=headers, json={**SETTINGS, 'pix_key_type': None}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_settings_rejects_key_not_matching_type(client: AsyncClient):
    headers = await auth_headers(client)

    response = await client.put(
        URL, headers=headers, json={**SETTINGS, 'pix_key_type': 'cpf'}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_settings_normalizes_key(client: AsyncClient):
    headers = await auth_headers(client)

    saved = await client.put(
        URL,
        headers=headers,
        json={
            **SETTINGS,
            'pix_key': '(11) 91234-5678',
            'pix_key_type': 'phone',
        },
    )

    assert saved.status_code == HTTPStatus.OK, saved.text
    assert saved.json()['pix_key'] == '+5511912345678'
    assert saved.json()['pix_key_type'] == 'phone'


@pytest.mark.asyncio
async def test_settings_type_without_key_is_dropped(client: AsyncClient):
    headers = await auth_headers(client)

    saved = await client.put(
        URL,
        headers=headers,
        json={**SETTINGS, 'pix_key': '', 'pix_key_type': 'cpf'},
    )

    assert saved.status_code == HTTPStatus.OK, saved.text
    assert saved.json()['pix_key'] is None
    assert saved.json()['pix_key_type'] is None
