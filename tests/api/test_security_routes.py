from http import HTTPStatus

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_master_context_route_was_removed(
    client: AsyncClient,
) -> None:
    response = await client.get('/api/v1/masters/context/123456')

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('method', 'url'),
    [
        ('POST', '/api/v1/telegram/webhook'),
        ('GET', '/api/v1/telegram/me'),
        ('POST', '/api/v1/onboarding'),
        ('POST', '/api/v1/auth/telegram/link-token'),
        ('POST', '/api/v1/auth/telegram/setup-token'),
    ],
)
async def test_telegram_routes_were_removed(
    client: AsyncClient,
    method: str,
    url: str,
) -> None:
    response = await client.request(method, url, json={})

    assert response.status_code in {
        HTTPStatus.NOT_FOUND,
        HTTPStatus.METHOD_NOT_ALLOWED,
    }
