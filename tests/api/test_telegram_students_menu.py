from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.modality import Modality
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


def expected_empty_modalities_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '✅ Concluir',
                    'callback_data': 'academy_modalities:finish',
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


async def mock_telegram_service(
    monkeypatch: pytest.MonkeyPatch,
    secret: str,
    sent_messages: list[dict[str, Any]],
    answered_callbacks: list[str],
) -> None:
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


async def post_students_menu_callback(
    client: AsyncClient,
    secret: str,
    telegram_user_id: int,
) -> Any:
    return await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json={
            'update_id': 3,
            'callback_query': {
                'id': 'callback-students',
                'from': {
                    'id': telegram_user_id,
                    'first_name': 'Thiago',
                },
                'message': {
                    'chat': {
                        'id': telegram_user_id,
                        'type': 'private',
                    },
                },
                'data': 'menu:students',
            },
        },
    )


@pytest.mark.asyncio
async def test_telegram_webhook_should_require_modality_before_students(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []
    answered_callbacks: list[str] = []

    _onboarding_response, payload = await register_onboarding(client)

    await mock_telegram_service(
        monkeypatch=monkeypatch,
        secret=secret,
        sent_messages=sent_messages,
        answered_callbacks=answered_callbacks,
    )

    response = await post_students_menu_callback(
        client=client,
        secret=secret,
        telegram_user_id=payload['telegram_user_id'],
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'status': 'academy_modalities_required_before_students'
    }
    assert answered_callbacks == ['callback-students']

    assert sent_messages == [
        {
            'chat_id': payload['telegram_user_id'],
            'text': (
                'Antes de cadastrar alunos, você precisa configurar '
                'pelo menos uma modalidade da sua academia.\n\n'
                'Selecione abaixo as modalidades que existem na sua '
                'academia 👇'
            ),
        },
        {
            'chat_id': payload['telegram_user_id'],
            'text': (
                '🏫 Modalidades da academia\n\n'
                'Selecione as modalidades que existem na sua academia.\n\n'
                'Toque em uma modalidade para marcar ou desmarcar.'
            ),
            'reply_markup': expected_empty_modalities_reply_markup(),
        },
    ]


@pytest.mark.asyncio
async def test_telegram_webhook_should_open_students_menu_callback_query(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []
    answered_callbacks: list[str] = []

    onboarding_response, payload = await register_onboarding(client)
    onboarding_body = onboarding_response.json()

    modality = Modality(
        name='Taekwondo',
        emoji='🥋',
        is_active=True,
    )
    db_session.add(modality)
    await db_session.flush()

    academy_modality = AcademyModality(
        academy_id=onboarding_body['academy_id'],
        modality_id=modality.id,
    )
    db_session.add(academy_modality)
    await db_session.commit()

    await mock_telegram_service(
        monkeypatch=monkeypatch,
        secret=secret,
        sent_messages=sent_messages,
        answered_callbacks=answered_callbacks,
    )

    response = await post_students_menu_callback(
        client=client,
        secret=secret,
        telegram_user_id=payload['telegram_user_id'],
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'students_menu_sent'}
    assert answered_callbacks == ['callback-students']

    assert sent_messages == [
        {
            'chat_id': payload['telegram_user_id'],
            'text': ('👥 Alunos\n\nEscolha uma opção abaixo 👇'),
            'reply_markup': expected_students_menu_reply_markup(),
        }
    ]
