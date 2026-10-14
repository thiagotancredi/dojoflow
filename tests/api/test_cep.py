from http import HTTPStatus

import pytest
from httpx import AsyncClient

from dojoflow.integrations.cep.client import CepClient
from dojoflow.integrations.cep.schemas import CepAddress
from tests.helpers.auth import auth_headers


@pytest.mark.asyncio
async def test_cep_found(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_search(self: CepClient, zip_code: str) -> CepAddress:
        return CepAddress(
            zip_code=zip_code,
            street='Rua A',
            neighborhood='Centro',
            city='Goiânia',
            state='GO',
            provider='fake',
        )

    monkeypatch.setattr(CepClient, 'search', fake_search)
    headers = await auth_headers(client)

    response = await client.get('/api/v1/cep/74000000', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['city'] == 'Goiânia'


@pytest.mark.asyncio
async def test_cep_not_found(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_search(self: CepClient, zip_code: str) -> None:
        return None

    monkeypatch.setattr(CepClient, 'search', fake_search)
    headers = await auth_headers(client)

    response = await client.get('/api/v1/cep/74000000', headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'CEP_NOT_FOUND'


@pytest.mark.asyncio
async def test_cep_rejects_malformed_zip(client: AsyncClient) -> None:
    headers = await auth_headers(client)

    response = await client.get('/api/v1/cep/123', headers=headers)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
