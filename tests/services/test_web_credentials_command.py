from typing import Any

import pytest
from httpx import AsyncClient

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from tests.helpers.onboarding import register_onboarding


@pytest.mark.asyncio
async def test_web_command_sends_setup_link(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', 'secret')
    monkeypatch.setattr(settings, 'WEB_APP_URL', 'https://app.dojoflow.test')
    sent: list[dict[str, Any]] = []

    async def fake_send_message(
        self: TelegramService,
        **kwargs: Any,
    ) -> dict[str, Any]:
        sent.append(kwargs)
        return {'ok': True}

    monkeypatch.setattr(TelegramService, 'send_message', fake_send_message)
    _, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    response = await client.post(
        '/api/v1/telegram/webhook',
        headers={'X-Telegram-Bot-Api-Secret-Token': 'secret'},
        json={
            'update_id': 1,
            'message': {
                'message_id': 1,
                'date': 0,
                'chat': {'id': telegram_user_id, 'type': 'private'},
                'from': {
                    'id': telegram_user_id,
                    'is_bot': False,
                    'first_name': 'Mestre',
                },
                'text': '/web',
            },
        },
    )

    assert response.json() == {'status': 'web_setup_token_sent'}
    text = sent[-1]['text']
    assert 'https://app.dojoflow.test/definir-acesso?token=' in text
    assert 'POST /api/v1/auth/set-credentials' not in text
