from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from dojoflow.services.telegram_bot.handlers.students import (
    StudentsMenuHandler,
)
from dojoflow.shared.telegram_enums import TelegramStep

CHAT_ID = 123
STATE_ID = 10
DUE_DAY = 7
ACADEMY_ID = 99
FAMILY_EMOJI = '\U0001f468\u200d\U0001f469\u200d\U0001f467'


def make_external_responsible_context() -> dict[str, Any]:
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
            {
                'relationship': 'mother',
                'name': 'Mãe da Lulu',
                'phone': '62981441450',
                'phone_is_whatsapp': True,
                'email': 'mae@example.com',
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
    }


@pytest.mark.asyncio
async def test_due_day_sends_confirmation_external_responsible() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_student_due_day_message(
        chat_id=CHAT_ID,
        due_day_text=str(DUE_DAY),
        state_id=STATE_ID,
        context_data=make_external_responsible_context(),
    )

    assert result == {'status': 'waiting_student_confirmation'}

    state_service.update_student_creation_context.assert_awaited_once()
    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )

    assert update_kwargs['state_id'] == STATE_ID
    assert (
        update_kwargs['next_step'] == TelegramStep.WAITING_STUDENT_CONFIRMATION
    )
    assert update_kwargs['context_data']['due_day'] == DUE_DAY
    assert update_kwargs['context_data']['is_exempt'] is False

    telegram_service.send_message.assert_awaited_once()
    send_kwargs = telegram_service.send_message.await_args.kwargs

    assert send_kwargs['chat_id'] == CHAT_ID

    summary_text = send_kwargs['text']
    reply_markup = send_kwargs['reply_markup']

    assert '📋 Resumo do cadastro' in summary_text
    assert '📞 Contato\nTelefone: Não informado' not in summary_text
    assert f'{FAMILY_EMOJI} Responsáveis' in summary_text
    assert 'Pai: Thiago Tancredi' in summary_text
    assert 'Mãe: Mãe da Lulu' in summary_text
    assert '\n\n💰 Mensalidade\n' in summary_text
    assert 'Valor: R$ 350.00' in summary_text
    assert 'Vencimento: dia 7' in summary_text
    assert 'Está tudo certo?' in summary_text

    assert reply_markup['inline_keyboard'][0][0] == {
        'text': '✅ Confirmar cadastro',
        'callback_data': 'students:create:confirm',
    }
    assert reply_markup['inline_keyboard'][1][0] == {
        'text': '❌ Cancelar cadastro',
        'callback_data': 'students:create:cancel',
    }


def make_self_responsible_context() -> dict[str, Any]:
    return {
        'student_name': 'Naruto Uzumaki',
        'modality_id': 1,
        'modality_name': 'Taekwondo',
        'sex': 'masculino',
        'responsible_type': 'self',
        'phone': '62999999999',
        'is_whatsapp': True,
        'address': {
            'zip_code': '74815705',
            'street': 'Rua Natal',
            'neighborhood': 'Alto da Glória',
            'city': 'Goiânia',
            'state': 'GO',
            'number': '327',
            'complement': None,
        },
        'cpf': '12345678911',
        'instagram': 'narutouzumaki',
        'email': 'naruto@example.com',
        'birth_date': '1994-01-24',
        'monthly_fee': '250.00',
    }


@pytest.mark.asyncio
async def test_due_day_sends_confirmation_self_responsible() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_student_due_day_message(
        chat_id=CHAT_ID,
        due_day_text=str(DUE_DAY),
        state_id=STATE_ID,
        context_data=make_self_responsible_context(),
    )

    assert result == {'status': 'waiting_student_confirmation'}

    state_service.update_student_creation_context.assert_awaited_once()
    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )

    assert update_kwargs['state_id'] == STATE_ID
    assert (
        update_kwargs['next_step'] == TelegramStep.WAITING_STUDENT_CONFIRMATION
    )
    assert update_kwargs['context_data']['due_day'] == DUE_DAY
    assert update_kwargs['context_data']['is_exempt'] is False

    telegram_service.send_message.assert_awaited_once()
    send_kwargs = telegram_service.send_message.await_args.kwargs

    summary_text = send_kwargs['text']
    reply_markup = send_kwargs['reply_markup']

    assert '📋 Resumo do cadastro' in summary_text
    assert '👤 Aluno' in summary_text
    assert 'Nome: Naruto Uzumaki' in summary_text
    assert '📞 Contato' in summary_text
    assert 'Telefone: 62999999999' in summary_text
    assert 'WhatsApp: Sim' in summary_text
    assert f'{FAMILY_EMOJI} Responsáveis' in summary_text
    assert 'Próprio aluno' in summary_text
    assert '\n\n💰 Mensalidade\n' in summary_text
    assert 'Valor: R$ 250.00' in summary_text
    assert 'Vencimento: dia 7' in summary_text
    assert 'Está tudo certo?' in summary_text

    assert reply_markup['inline_keyboard'][0][0] == {
        'text': '✅ Confirmar cadastro',
        'callback_data': 'students:create:confirm',
    }
    assert reply_markup['inline_keyboard'][1][0] == {
        'text': '❌ Cancelar cadastro',
        'callback_data': 'students:create:cancel',
    }


@pytest.mark.asyncio
async def test_students_list_sends_students_as_buttons() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()

    student_service.list_by_academy.return_value = [
        SimpleNamespace(id=1, name='Lulu Nuna'),
        SimpleNamespace(id=2, name='Naruto Uzumaki'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler._process_students_list(
        chat_id=CHAT_ID,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'students_list_sent'}

    student_service.list_by_academy.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
    )

    telegram_service.send_message.assert_awaited_once()
    send_kwargs = telegram_service.send_message.await_args.kwargs

    assert send_kwargs['chat_id'] == CHAT_ID
    assert send_kwargs['text'] == (
        '📋 Lista de alunos\n\nToque em um aluno para ver as informações.'
    )
    assert send_kwargs['reply_markup'] == {
        'inline_keyboard': [
            [
                {
                    'text': 'ℹ️ Lulu Nuna',
                    'callback_data': 'students:details:1',
                },
            ],
            [
                {
                    'text': 'ℹ️ Naruto Uzumaki',
                    'callback_data': 'students:details:2',
                },
            ],
            [
                {
                    'text': '🔙 Voltar ao menu',
                    'callback_data': 'menu:students',
                },
            ],
        ],
    }


@pytest.mark.asyncio
async def test_student_search_sends_result_as_buttons() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()

    student_service.search_by_name.return_value = [
        SimpleNamespace(id=1, name='Lulu Nuna'),
        SimpleNamespace(id=2, name='Naruto Uzumaki'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_student_search_message(
        chat_id=CHAT_ID,
        search_text='  Lu  ',
        state_id=STATE_ID,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'students_search_sent'}

    student_service.search_by_name.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        search_text='Lu',
    )
    state_service.complete_current_flow.assert_awaited_once_with(STATE_ID)

    telegram_service.send_message.assert_awaited_once()
    send_kwargs = telegram_service.send_message.await_args.kwargs

    assert send_kwargs['chat_id'] == CHAT_ID
    assert send_kwargs['text'] == (
        '🔎 Resultado da pesquisa\n\n'
        'Toque em um aluno para ver as informações.'
    )
    assert send_kwargs['reply_markup'] == {
        'inline_keyboard': [
            [
                {
                    'text': 'ℹ️ Lulu Nuna',
                    'callback_data': 'students:details:1',
                },
            ],
            [
                {
                    'text': 'ℹ️ Naruto Uzumaki',
                    'callback_data': 'students:details:2',
                },
            ],
            [
                {
                    'text': '🔙 Voltar ao menu',
                    'callback_data': 'menu:students',
                },
            ],
        ],
    }
