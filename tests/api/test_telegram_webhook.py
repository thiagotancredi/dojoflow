from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.models.academy import Academy
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.master import Master
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.models.telegram_conversation_state import (
    TelegramConversationState,
)
from dojoflow.shared.telegram_enums import TelegramFlow, TelegramStep
from tests.helpers.onboarding import register_onboarding

TELEGRAM_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'
DUE_DAY = 7
NAME_EDIT_PROMPT = 'Nome atual:\nThiago\n\nDigite o novo nome do aluno.'
MONTHLY_FEE_EDIT_PROMPT = (
    'Valor atual:\nR$ 250,00\n\nDigite o novo valor da mensalidade.'
)


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
                    'text': '🏫 Minha Academia',
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


def make_fake_send_message(
    sent_messages: list[dict[str, Any]],
):
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

    return fake_send_message


def build_message_payload(
    telegram_user_id: int,
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
                'id': telegram_user_id,
                'type': 'private',
            },
            'text': text,
        },
    }


def build_callback_payload(
    telegram_user_id: int,
    update_id: int,
    callback_data: str,
) -> dict[str, Any]:
    return {
        'update_id': update_id,
        'callback_query': {
            'id': f'callback-{update_id}',
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
            'data': callback_data,
        },
    }


async def upsert_state(
    db_session: AsyncSession,
    telegram_user_id: int,
    current_flow: TelegramFlow,
    current_step: TelegramStep,
    context_data: dict[str, Any],
) -> None:
    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    if state is None:
        state = TelegramConversationState(
            telegram_user_id=telegram_user_id,
            current_flow=current_flow,
            current_step=current_step,
            context_data=context_data,
        )
        db_session.add(state)
    else:
        state.current_flow = current_flow
        state.current_step = current_step
        state.context_data = context_data

    await db_session.commit()


async def setup_student_for_edit(
    client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[int, int]:
    onboarding_response, payload = await register_onboarding(client)
    academy_id = onboarding_response.json()['academy_id']

    modality_1 = Modality(
        name='Taekwondo',
        emoji='🥋',
        is_active=True,
    )
    modality_2 = Modality(
        name='Jiu-jitsu',
        emoji='🤼',
        is_active=True,
    )
    db_session.add_all([modality_1, modality_2])
    await db_session.flush()

    db_session.add_all([
        AcademyModality(
            academy_id=academy_id,
            modality_id=modality_1.id,
        ),
        AcademyModality(
            academy_id=academy_id,
            modality_id=modality_2.id,
        ),
    ])

    student = Student(
        academy_id=academy_id,
        name='Thiago',
        cpf='12345678911',
        instagram='thiago',
        email='thiago@example.com',
    )
    db_session.add(student)
    await db_session.flush()

    db_session.add(
        Enrollment(
            academy_id=academy_id,
            student_id=student.id,
            modality_id=modality_1.id,
            monthly_fee='250.00',
            due_day=7,
            is_exempt=False,
        )
    )
    await db_session.commit()

    return payload['telegram_user_id'], student.id


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
                '🏫 Minha Academia: alterar seus dados, dados da academia '
                'e modalidades.\n\n'
                'Comandos úteis:\n'
                '📌 menu - mostra o menu principal\n'
                '❌ cancelar - cancela a operação atual\n'
                '❓ ajuda - mostra esta mensagem novamente'
            ),
            'reply_markup': expected_main_menu_reply_markup(),
        }
    ]


def make_student_confirmation_context() -> dict[str, Any]:
    return {
        'student_name': 'Lulu Nuna',
        'modality_id': 1,
        'modality_name': 'Taekwondo',
        'sex': 'feminino',
        'responsible_type': 'external',
        'responsibles': [
            {
                'relationship': 'father',
                'name': 'Thiago Tancredi',
                'phone': '62982551800',
                'phone_is_whatsapp': True,
                'email': 'pai@example.com',
            },
        ],
        'address': {
            'zip_code': '74815705',
            'street': 'Rua Natal',
            'neighborhood': 'Alto da Glória',
            'city': 'Goiânia',
            'state': 'GO',
            'number': '327',
            'complement': 'Apartamento 902 Bloco A',
        },
        'cpf': '43256798712',
        'instagram': 'lunanuninha',
        'email': 'lunaninha@example.com',
        'birth_date': '2020-09-24',
        'monthly_fee': '350.00',
        'due_day': 7,
        'is_exempt': False,
    }


def make_pending_field_confirmation_context() -> dict[str, Any]:
    context_data = make_student_confirmation_context()
    context_data.pop('due_day')
    context_data.pop('is_exempt')
    context_data['pending_field_confirmation'] = {
        'source_step': TelegramStep.WAITING_STUDENT_DUE_DAY,
        'field_label': 'o dia de vencimento',
        'value': DUE_DAY,
        'display_value': f'Dia {DUE_DAY}',
        'prompt_text': (
            'Qual é o dia de vencimento da mensalidade?\n\n'
            'Digite um dia entre 1 e 28.\n\n'
            'Exemplo:\n'
            '10'
        ),
    }

    return context_data


@pytest.mark.asyncio
async def test_webhook_resends_student_confirmation_message(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    _onboarding_response, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

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

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    if state is None:
        state = TelegramConversationState(
            telegram_user_id=telegram_user_id,
            current_flow=TelegramFlow.STUDENT_CREATION,
            current_step=TelegramStep.WAITING_STUDENT_CONFIRMATION,
            context_data=make_student_confirmation_context(),
        )
        db_session.add(state)
    else:
        state.current_flow = TelegramFlow.STUDENT_CREATION
        state.current_step = TelegramStep.WAITING_STUDENT_CONFIRMATION
        state.context_data = make_student_confirmation_context()

    await db_session.commit()

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json={
            'update_id': 999,
            'message': {
                'message_id': 999,
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
    assert response.json() == {'status': 'waiting_student_confirmation'}

    assert len(sent_messages) == 1

    message = sent_messages[0]
    summary_text = message['text']
    reply_markup = message['reply_markup']

    family_emoji = '\U0001f468\u200d\U0001f469\u200d\U0001f467'

    assert '📋 Resumo do cadastro' in summary_text
    assert '👥 Alunos' not in summary_text
    assert 'Escolha uma opção abaixo' not in summary_text
    assert '📞 Contato\nTelefone: Não informado' not in summary_text
    assert f'{family_emoji} Responsáveis' in summary_text
    assert '\n\n💰 Mensalidade\n' in summary_text

    assert reply_markup['inline_keyboard'][0][0] == {
        'text': '✅ Confirmar cadastro',
        'callback_data': 'students:create:confirm',
    }
    assert reply_markup['inline_keyboard'][1][0] == {
        'text': '❌ Cancelar cadastro',
        'callback_data': 'students:create:cancel',
    }


@pytest.mark.asyncio
async def test_webhook_resends_student_field_confirmation_message(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    _onboarding_response, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_CREATION,
        current_step=TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
        context_data=make_pending_field_confirmation_context(),
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_message_payload(
            telegram_user_id=telegram_user_id,
            update_id=1000,
            text='qualquer coisa',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_field_confirmation'}

    message = sent_messages[0]
    assert 'Confirme o dia de vencimento' in message['text']
    assert message['reply_markup']['inline_keyboard'][0][0] == {
        'text': '✅ Confirmar',
        'callback_data': 'students:create:field:confirm',
    }


@pytest.mark.asyncio
async def test_webhook_processes_confirm_field_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    _onboarding_response, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_CREATION,
        current_step=TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
        context_data=make_pending_field_confirmation_context(),
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=1001,
            callback_data='students:create:field:confirm',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_confirmation'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    assert state is not None
    assert state.current_step == TelegramStep.WAITING_STUDENT_CONFIRMATION
    assert state.context_data['due_day'] == DUE_DAY
    assert state.context_data['is_exempt'] is False
    assert 'pending_field_confirmation' not in state.context_data
    assert '📋 Resumo do cadastro' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_processes_rewrite_field_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    _onboarding_response, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_CREATION,
        current_step=TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
        context_data=make_pending_field_confirmation_context(),
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=1002,
            callback_data='students:create:field:rewrite',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_due_day'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    assert state is not None
    assert state.current_step == TelegramStep.WAITING_STUDENT_DUE_DAY
    assert 'pending_field_confirmation' not in state.context_data
    assert (
        'Qual é o dia de vencimento da mensalidade?'
        in (sent_messages[0]['text'])
    )


@pytest.mark.asyncio
async def test_webhook_processes_cancel_from_field_confirmation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    _onboarding_response, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_CREATION,
        current_step=TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
        context_data=make_pending_field_confirmation_context(),
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=1003,
            callback_data='students:create:cancel',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'student_creation_cancelled'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    assert state is not None
    assert state.current_step == TelegramStep.COMPLETED
    assert state.context_data == {}
    assert 'Cadastro de aluno cancelado' in sent_messages[0]['text']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('step', 'callback_data', 'expected_status', 'expected_text'),
    [
        (
            TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
            'students:create:address:search_again',
            'waiting_student_address_reference_search',
            'Digite o nome do aluno que já possui o endereço',
        ),
        (
            TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
            'students:create:address:back',
            'waiting_student_address_choice',
            'Como deseja informar o endereço do aluno?',
        ),
        (
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH,
            'students:create:responsible:search_again',
            'waiting_student_responsible_reference_search',
            'Digite o nome do aluno que já possui esse mesmo responsável.',
        ),
        (
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH,
            'students:create:responsible:back',
            'waiting_student_responsible_choice',
            'Como deseja informar o responsável do aluno?',
        ),
    ],
)
async def test_webhook_processes_reference_navigation_callbacks(  # noqa: PLR0913, PLR0917
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    step: TelegramStep,
    callback_data: str,
    expected_status: str,
    expected_text: str,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    _onboarding_response, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    context_data = {
        'student_name': 'Naruto',
        'responsible_type': 'external',
        'address_reference_student_name': 'Lukito Referencia',
        'address_reference_student_id': 1,
        'address_reference': {'street': 'Rua Natal'},
        'address': {'street': 'Rua Antiga'},
    }

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_CREATION,
        current_step=step,
        context_data=context_data,
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=1004,
            callback_data=callback_data,
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': expected_status}
    assert expected_text in sent_messages[0]['text']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'step',
    [
        TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
        TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH,
    ],
)
async def test_webhook_processes_cancel_during_reference_reuse(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    step: TelegramStep,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    _onboarding_response, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    monkeypatch.setattr(
        settings,
        'TELEGRAM_WEBHOOK_SECRET',
        secret,
    )
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_CREATION,
        current_step=step,
        context_data={'student_name': 'Naruto'},
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=1005,
            callback_data='students:create:cancel',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'student_creation_cancelled'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )

    assert state is not None
    assert state.current_step == TelegramStep.COMPLETED
    assert state.context_data == {}
    assert 'Cadastro de aluno cancelado' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_opens_student_edit_menu(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=2001,
            callback_data=f'students:edit:{student_id}',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_menu'}
    assert sent_messages[0]['text'] == '✏️ Editar aluno\n\nO que deseja editar?'


@pytest.mark.asyncio
async def test_webhook_opens_student_edit_basic_data_menu(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_MENU,
        context_data={'student_id': student_id},
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=2002,
            callback_data='students:edit:section:basic',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_basic_data'}
    assert 'Escolha o campo que deseja editar' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_opens_student_edit_monthly_fee_menu(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_MENU,
        context_data={'student_id': student_id},
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=20021,
            callback_data='students:edit:section:monthly_fee',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'status': 'waiting_student_edit_monthly_fee_menu'
    }
    assert sent_messages[0]['text'] == (
        '💰 Mensalidade\n\nEscolha o campo que deseja editar:'
    )


@pytest.mark.asyncio
async def test_webhook_opens_student_edit_due_day_field(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE_MENU,
        context_data={'student_id': student_id},
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=20022,
            callback_data='students:edit:monthly_fee:due_day',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_due_day'}
    assert 'Digite o novo dia de vencimento.' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_opens_student_edit_name_field(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_BASIC_DATA,
        context_data={'student_id': student_id},
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=2003,
            callback_data='students:edit:field:name',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_name'}
    assert 'Digite o novo nome do aluno.' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_message_confirmation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_NAME,
        context_data={'student_id': student_id},
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_message_payload(
            telegram_user_id=telegram_user_id,
            update_id=2004,
            text='Tiago',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_confirmation'}
    assert 'Confirmar alteração de nome?' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_monthly_fee_message_confirmation(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE,
        context_data={'student_id': student_id},
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_message_payload(
            telegram_user_id=telegram_user_id,
            update_id=20041,
            text='180,00',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_confirmation'}
    assert 'Confirmar alteração de valor da mensalidade?' in (
        sent_messages[0]['text']
    )
    assert 'R$ 180,00' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_confirm_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': TelegramStep.WAITING_STUDENT_EDIT_NAME.value,
                'field': 'name',
                'field_label': 'Nome',
                'current_display': 'Thiago',
                'value': 'Tiago',
                'new_display': 'Tiago',
                'prompt_text': NAME_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=2005,
            callback_data='students:edit:confirm',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'student_edit_saved'}

    student = await db_session.get(Student, student_id)
    assert student is not None
    assert student.name == 'Tiago'
    assert sent_messages[0]['text'] == 'Alteração salva com sucesso! ✅'
    assert 'Nome: Tiago' in sent_messages[1]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_monthly_fee_confirm_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': (
                    TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE.value
                ),
                'field': 'monthly_fee',
                'field_label': 'Valor da mensalidade',
                'current_display': 'R$ 250,00',
                'value': '180.00',
                'new_display': 'R$ 180,00',
                'prompt_text': MONTHLY_FEE_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=20051,
            callback_data='students:edit:confirm',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'student_edit_saved'}

    enrollment = await db_session.scalar(
        select(Enrollment).where(Enrollment.student_id == student_id)
    )
    assert enrollment is not None
    assert str(enrollment.monthly_fee) == '180.00'
    assert sent_messages[0]['text'] == 'Alteração salva com sucesso! ✅'
    assert 'Valor: R$ 180.00' in sent_messages[1]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_rewrite_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': TelegramStep.WAITING_STUDENT_EDIT_NAME.value,
                'field': 'name',
                'field_label': 'Nome',
                'current_display': 'Thiago',
                'value': 'Tiago',
                'new_display': 'Tiago',
                'prompt_text': NAME_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=2006,
            callback_data='students:edit:rewrite',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_name'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )
    assert state is not None
    assert state.current_step == TelegramStep.WAITING_STUDENT_EDIT_NAME
    assert 'Digite o novo nome do aluno.' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_monthly_fee_rewrite_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': (
                    TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE.value
                ),
                'field': 'monthly_fee',
                'field_label': 'Valor da mensalidade',
                'current_display': 'R$ 250,00',
                'value': '180.00',
                'new_display': 'R$ 180,00',
                'prompt_text': MONTHLY_FEE_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=20061,
            callback_data='students:edit:rewrite',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_monthly_fee'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )
    assert state is not None
    assert state.current_step == TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE
    assert sent_messages[0]['text'] == MONTHLY_FEE_EDIT_PROMPT


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_back_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': TelegramStep.WAITING_STUDENT_EDIT_NAME.value,
                'field': 'name',
                'field_label': 'Nome',
                'current_display': 'Thiago',
                'value': 'Tiago',
                'new_display': 'Tiago',
                'prompt_text': NAME_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=2007,
            callback_data='students:edit:back',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'waiting_student_edit_basic_data'}
    assert 'Escolha o campo que deseja editar' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_monthly_fee_back_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': (
                    TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE.value
                ),
                'field': 'monthly_fee',
                'field_label': 'Valor da mensalidade',
                'current_display': 'R$ 250,00',
                'value': '180.00',
                'new_display': 'R$ 180,00',
                'prompt_text': MONTHLY_FEE_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=20071,
            callback_data='students:edit:back',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'status': 'waiting_student_edit_monthly_fee_menu'
    }
    assert sent_messages[0]['text'] == (
        '💰 Mensalidade\n\nEscolha o campo que deseja editar:'
    )


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_cancel_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': TelegramStep.WAITING_STUDENT_EDIT_NAME.value,
                'field': 'name',
                'field_label': 'Nome',
                'current_display': 'Thiago',
                'value': 'Tiago',
                'new_display': 'Tiago',
                'prompt_text': NAME_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=2008,
            callback_data='students:edit:cancel',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'student_edit_cancelled'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )
    student = await db_session.get(Student, student_id)

    assert state is not None
    assert state.current_step == TelegramStep.COMPLETED
    assert student is not None
    assert student.name == 'Thiago'
    assert 'Nome: Thiago' in sent_messages[0]['text']


@pytest.mark.asyncio
async def test_webhook_processes_student_edit_monthly_fee_cancel_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []

    telegram_user_id, student_id = await setup_student_for_edit(
        client,
        db_session,
    )

    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', secret)
    monkeypatch.setattr(
        TelegramService,
        'send_message',
        make_fake_send_message(sent_messages),
    )

    await upsert_state(
        db_session=db_session,
        telegram_user_id=telegram_user_id,
        current_flow=TelegramFlow.STUDENT_EDIT,
        current_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
        context_data={
            'student_id': student_id,
            'pending_student_edit': {
                'action': 'update',
                'source_step': (
                    TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE.value
                ),
                'field': 'monthly_fee',
                'field_label': 'Valor da mensalidade',
                'current_display': 'R$ 250,00',
                'value': '180.00',
                'new_display': 'R$ 180,00',
                'prompt_text': MONTHLY_FEE_EDIT_PROMPT,
                'prompt_reply_markup': {'inline_keyboard': []},
            },
        },
    )

    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={TELEGRAM_SECRET_HEADER: secret},
        json=build_callback_payload(
            telegram_user_id=telegram_user_id,
            update_id=20081,
            callback_data='students:edit:cancel',
        ),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'student_edit_cancelled'}

    state = await db_session.scalar(
        select(TelegramConversationState).where(
            TelegramConversationState.telegram_user_id == telegram_user_id
        )
    )
    enrollment = await db_session.scalar(
        select(Enrollment).where(Enrollment.student_id == student_id)
    )

    assert state is not None
    assert state.current_step == TelegramStep.COMPLETED
    assert enrollment is not None
    assert str(enrollment.monthly_fee) == '250.00'
    assert 'Valor: R$ 250.00' in sent_messages[0]['text']
