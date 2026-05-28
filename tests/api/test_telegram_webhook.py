from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.models.academy import Academy
from dojoflow.models.master import Master
from dojoflow.models.telegram_conversation_state import (
    TelegramConversationState,
)
from dojoflow.shared.telegram_enums import TelegramFlow, TelegramStep
from tests.helpers.onboarding import register_onboarding

TELEGRAM_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'


def expected_main_menu_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '👥 Alunos',
                    'callback_data': 'menu:students',
                },
                {
                    'text': '💰 Mensalidades',
                    'callback_data': 'menu:monthly_fees',
                },
            ],
            [
                {
                    'text': '✅ Pagamentos',
                    'callback_data': 'menu:payments',
                },
                {
                    'text': '📊 Relatórios',
                    'callback_data': 'menu:reports',
                },
            ],
            [
                {
                    'text': '🏫 Minha academia',
                    'callback_data': 'menu:academy',
                },
            ],
            [
                {
                    'text': '❓ Ajuda',
                    'callback_data': 'menu:help',
                },
            ],
        ]
    }


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
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        message: dict[str, Any] = {
            'chat_id': chat_id,
            'text': text,
        }

        if reply_markup is not None:
            message['reply_markup'] = reply_markup

        sent_messages.append(message)

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


@pytest.mark.asyncio
async def test_telegram_webhook_should_complete_onboarding_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    telegram_user_id = 123456789
    chat_id = 987654321
    academy_name = 'Academia Dragão Azul'
    master_name = 'Thiago Tancredi'
    sent_messages: list[dict[str, Any]] = []

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

    def build_payload(
        update_id: int,
        text: str,
    ) -> dict[str, Any]:
        return {
            'update_id': update_id,
            'message': {
                'message_id': update_id,
                'from': {
                    'id': telegram_user_id,
                    'first_name': 'Thiago',
                },
                'chat': {
                    'id': chat_id,
                    'type': 'private',
                },
                'text': text,
            },
        }

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

    start_response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json=build_payload(update_id=1, text='/start'),
    )

    academy_response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json=build_payload(update_id=2, text=academy_name),
    )

    master_response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json=build_payload(update_id=3, text=master_name),
    )

    assert start_response.status_code == HTTPStatus.OK
    assert start_response.json() == {'status': 'onboarding_started'}

    assert academy_response.status_code == HTTPStatus.OK
    assert academy_response.json() == {'status': 'academy_name_received'}

    assert master_response.status_code == HTTPStatus.OK
    assert master_response.json() == {'status': 'onboarding_completed'}

    academy = await db_session.scalar(
        select(Academy).where(Academy.name == academy_name)
    )
    master = await db_session.scalar(
        select(Master).where(Master.telegram_user_id == telegram_user_id)
    )
    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    assert academy is not None
    assert master is not None
    assert state is not None

    assert master.name == master_name
    assert master.academy_id == academy.id
    assert master.telegram_user_id == telegram_user_id

    assert state.academy_id == academy.id
    assert state.master_id == master.id
    assert state.current_flow == TelegramFlow.ONBOARDING
    assert state.current_step == TelegramStep.COMPLETED

    assert sent_messages == [
        {
            'chat_id': chat_id,
            'text': (
                'Bem-vindo ao DojoFlow! 🥋\n\n'
                'Vamos iniciar seu cadastro.\n'
                'Qual é o nome da sua academia?'
            ),
        },
        {
            'chat_id': chat_id,
            'text': (
                f'Academia "{academy_name}" anotada. 🥋\n\n'
                'Agora me informe seu nome.'
            ),
        },
        {
            'chat_id': chat_id,
            'text': (
                'Cadastro concluído com sucesso! 🥋\n\n'
                f'Academia: {academy_name}\n'
                f'Mestre: {master_name}'
            ),
        },
    ]


@pytest.mark.asyncio
async def test_telegram_webhook_should_process_message_from_registered_master(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    onboarding_response, payload = await register_onboarding(client)
    onboarding_body = onboarding_response.json()

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
                    'id': payload['telegram_user_id'],
                    'first_name': 'Thiago',
                },
                'chat': {
                    'id': payload['telegram_user_id'],
                    'type': 'private',
                },
                'text': 'oi',
            },
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'message_processed'}

    assert sent_messages == [
        {
            'chat_id': payload['telegram_user_id'],
            'text': (
                f'Olá, {payload["master_name"]}! 🥋\n\n'
                f'🏫 Academia: {payload["academy_name"]}\n\n'
                'Escolha uma opção abaixo 👇'
            ),
            'reply_markup': expected_main_menu_reply_markup(),
        }
    ]

    assert onboarding_body['academy_id'] is not None
    assert onboarding_body['master_id'] is not None


@pytest.mark.asyncio
async def test_telegram_webhook_should_process_help_callback_query(
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
            'update_id': 2,
            'callback_query': {
                'id': 'callback-1',
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
                'data': 'menu:help',
            },
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'help_sent'}
    assert answered_callbacks == ['callback-1']

    assert sent_messages == [
        {
            'chat_id': payload['telegram_user_id'],
            'text': (
                '❓ Ajuda - DojoFlow 🥋\n\n'
                'Use os botões do menu para navegar pelo sistema.\n\n'
                'Opções disponíveis:\n'
                '👥 Alunos: cadastrar, listar e buscar alunos.\n'
                '💰 Mensalidades: ver mensalidades em aberto, atrasadas, '
                'pagas e isentas.\n'
                '✅ Pagamentos: registrar pagamento normal, parcial '
                'ou adiantado.\n'
                '📊 Relatórios: ver resumo financeiro e taxas.\n'
                '🏫 Minha academia: alterar seus dados, dados da academia '
                'e modalidades.\n\n'
                'Comandos úteis:\n'
                '📌 menu - mostra o menu principal\n'
                '❌ cancelar - cancela a operação atual\n'
                '❓ ajuda - mostra esta mensagem novamente'
            ),
            'reply_markup': expected_main_menu_reply_markup(),
        }
    ]
