from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from tests.helpers.onboarding import register_onboarding

TELEGRAM_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'


def expected_students_menu_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '➕ Cadastrar novo aluno',
                    'callback_data': 'students:create',
                },
            ],
            [
                {
                    'text': '📋 Lista de alunos',
                    'callback_data': 'students:list',
                },
            ],
            [
                {
                    'text': '🔎 Procurar aluno pelo nome',
                    'callback_data': 'students:search',
                },
            ],
            [
                {
                    'text': '🔙 Voltar ao menu',
                    'callback_data': 'menu:main',
                },
            ],
        ]
    }


@pytest.mark.asyncio
async def test_telegram_webhook_should_open_students_menu_callback_query(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []
    answered_callbacks: list[str] = []

    _onboarding_response, payload = await register_onboarding(client)

    async def fake_send_message(
        _self: TelegramService,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        message: dict[str, Any] = {
            'chat_id': chat_id,
            'text': text,
        }

        if reply_markup is not None:
            message['reply_markup'] = reply_markup

        sent_messages.append(message)

    async def fake_answer_callback_query(
        _self: TelegramService,
        callback_query_id: str,
        text: str | None = None,
    ) -> None:
        answered_callbacks.append(callback_query_id)

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
    monkeypatch.setattr(
        TelegramService,
        'answer_callback_query',
        fake_answer_callback_query,
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json={
            'update_id': 3,
            'callback_query': {
                'id': 'callback-students',
                'from': {
                    'id': payload['telegram_user_id'],
                    'first_name': 'Thiago',
                },
                'message': {
                    'chat': {
                        'id': payload['telegram_user_id'],
                        'type': 'private',
                    },
                },
                'data': 'menu:students',
            },
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'students_menu_sent'}
    assert answered_callbacks == ['callback-students']

    assert sent_messages == [
        {
            'chat_id': payload['telegram_user_id'],
            'text': (
                '👥 Alunos\n\n'
                'Escolha uma opção abaixo 👇'
            ),
            'reply_markup': expected_students_menu_reply_markup(),
        }
    ]
