from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.services.billing import DEFAULT_MESSAGE_TEMPLATE
from tests.helpers.auth import auth_headers, other_academy_headers

URL = '/api/v1/academy/billing-settings'

SETTINGS = {
    'pix_key': 'dojo@exemplo.com',
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
        'recipient_name': None,
        'bank_details': None,
        'message_template': DEFAULT_MESSAGE_TEMPLATE,
    }
    assert DEFAULT_MESSAGE_TEMPLATE == (
        'Olá, {nome}! Tudo bem? 🥋\n\n'
        'Passando para lembrar que a mensalidade da {academia} está em '
        'aberto: {valor} ({meses}).\n\n'
        'Você pode pagar pelo Pix: {pix} ({recebedor}).\n\n'
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
