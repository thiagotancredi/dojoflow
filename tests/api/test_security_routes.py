from http import HTTPStatus

import pytest
from httpx import AsyncClient

from dojoflow.core.settings import settings


@pytest.mark.asyncio
async def test_master_context_route_was_removed(
    client: AsyncClient,
) -> None:
    response = await client.get('/api/v1/masters/context/123456')

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_secret(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', 'right')

    response = await client.post(
        '/api/v1/telegram/webhook',
        json={'update_id': 1},
        headers={'X-Telegram-Bot-Api-Secret-Token': 'wrong'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
