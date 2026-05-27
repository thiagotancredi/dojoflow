from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.models.telegram_conversation_state import (
    TelegramConversationState,
)
from dojoflow.shared.telegram_enums import TelegramFlow, TelegramStep

TELEGRAM_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'


@pytest.mark.asyncio
async def test_telegram_webhook_should_return_401_without_secret(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        'test-secret',
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        json={'update_id': 1},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        'detail': 'Invalid Telegram webhook secret.',
    }


@pytest.mark.asyncio
async def test_telegram_webhook_should_ignore_update_without_message(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json={'update_id': 1},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'ignored'}


@pytest.mark.asyncio
async def test_telegram_webhook_should_restart_invalid_state(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    telegram_user_id = 123456789
    sent_messages: list[dict[str, Any]] = []

    async def fake_send_message(
        _self: TelegramService,
        chat_id: int,
        text: str,
    ) -> None:
        sent_messages.append(
            {
                'chat_id': chat_id,
                'text': text,
            }
        )

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        fake_send_message,
    )

    invalid_state = TelegramConversationState(
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.ONBOARDING,
        current_step='unknown_step',
        context_data={
            'old_data': 'invalid',
        },
    )

    db_session.add(invalid_state)
    await db_session.commit()

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json={
            'update_id': 1,
            'message': {
                'message_id': 1,
                'from': {
                    'id': telegram_user_id,
                    'first_name': 'Thiago',
                },
                'chat': {
                    'id': telegram_user_id,
                    'type': 'private',
                },
                'text': 'qualquer coisa',
            },
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'onboarding_restarted'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    assert state is not None
    assert state.current_flow == TelegramFlow.ONBOARDING
    assert state.current_step == TelegramStep.WAITING_ACADEMY_NAME
    assert state.context_data == {}

    assert sent_messages == [
        {
            'chat_id': telegram_user_id,
            'text': (
                'Não consegui identificar em qual etapa do cadastro você '
                'estava.\n\n'
                'Vamos reiniciar seu cadastro.\n'
                'Qual é o nome da sua academia?'
            ),
        }
    ]
