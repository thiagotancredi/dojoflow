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
TELEGRAM_USER_ID = 321
EXPECTED_ADDRESS_REUSE_MESSAGES = 2


def extract_button_texts(
    reply_markup: dict[str, Any],
) -> list[str]:
    return [
        button['text']
        for row in reply_markup['inline_keyboard']
        for button in row
    ]


def extract_pending_field_confirmation(
    state_service: AsyncMock,
) -> dict[str, Any]:
    return state_service.update_student_creation_context.await_args.kwargs[
        'context_data'
    ]['pending_field_confirmation']


@pytest.mark.parametrize(
    ('runner', 'expected_step', 'expected_value', 'expected_display_value'),
    [
        (
            'cpf',
            TelegramStep.WAITING_STUDENT_CPF,
            '12345678911',
            '12345678911',
        ),
        (
            'instagram',
            TelegramStep.WAITING_STUDENT_INSTAGRAM,
            'narutouzumaki',
            '@narutouzumaki',
        ),
        (
            'email',
            TelegramStep.WAITING_STUDENT_EMAIL,
            'naruto@example.com',
            'naruto@example.com',
        ),
        (
            'birth_date',
            TelegramStep.WAITING_STUDENT_BIRTH_DATE,
            '1994-01-24',
            '24/01/1994',
        ),
        (
            'monthly_fee',
            TelegramStep.WAITING_STUDENT_MONTHLY_FEE,
            '250.00',
            'R$ 250.00',
        ),
        (
            'responsible_name',
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_NAME,
            'Thiago Tancredi',
            'Thiago Tancredi',
        ),
        (
            'responsible_phone',
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_PHONE,
            '62982551800',
            '62982551800',
        ),
        (
            'responsible_email',
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_EMAIL,
            'pai@example.com',
            'pai@example.com',
        ),
        (
            'address_zip_code',
            TelegramStep.WAITING_STUDENT_ADDRESS_ZIP_CODE,
            '74815705',
            '74815705',
        ),
        (
            'address_street',
            TelegramStep.WAITING_STUDENT_ADDRESS_STREET,
            'Rua Natal',
            'Rua Natal',
        ),
        (
            'address_neighborhood',
            TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD,
            'Alto da Glória',
            'Alto da Glória',
        ),
        (
            'address_number',
            TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER,
            '327',
            '327',
        ),
        (
            'address_complement',
            TelegramStep.WAITING_STUDENT_ADDRESS_COMPLEMENT,
            'Casa 2',
            'Casa 2',
        ),
    ],
)
@pytest.mark.asyncio
async def test_manual_fields_enter_intermediate_confirmation(  # noqa: PLR0912
    runner: str,
    expected_step: TelegramStep,
    expected_value: str,
    expected_display_value: str,
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    if runner == 'cpf':
        result = await handler.process_student_cpf_message(
            chat_id=CHAT_ID,
            cpf='12345678911',
            state_id=STATE_ID,
            context_data=make_self_responsible_context(),
        )
    elif runner == 'instagram':
        result = await handler.process_student_instagram_message(
            chat_id=CHAT_ID,
            instagram='NarutoUzumaki',
            state_id=STATE_ID,
            context_data=make_self_responsible_context(),
        )
    elif runner == 'email':
        result = await handler.process_student_email_message(
            chat_id=CHAT_ID,
            email='naruto@example.com',
            state_id=STATE_ID,
            context_data=make_self_responsible_context(),
        )
    elif runner == 'birth_date':
        result = await handler.process_student_birth_date_message(
            chat_id=CHAT_ID,
            birth_date_text='24/01/1994',
            state_id=STATE_ID,
            context_data=make_self_responsible_context(),
        )
    elif runner == 'monthly_fee':
        result = await handler.process_student_monthly_fee_message(
            chat_id=CHAT_ID,
            monthly_fee_text='250',
            state_id=STATE_ID,
            context_data=make_self_responsible_context(),
        )
    elif runner == 'responsible_name':
        result = await handler.process_student_responsible_name_message(
            chat_id=CHAT_ID,
            responsible_name='Thiago Tancredi',
            state_id=STATE_ID,
            context_data={
                'current_responsible': {
                    'relationship': 'father',
                },
            },
        )
    elif runner == 'responsible_phone':
        result = await handler.process_student_responsible_phone_message(
            chat_id=CHAT_ID,
            phone='62982551800',
            state_id=STATE_ID,
            context_data={
                'current_responsible': {
                    'relationship': 'father',
                    'name': 'Thiago Tancredi',
                },
            },
        )
    elif runner == 'responsible_email':
        result = await handler.process_student_responsible_email_message(
            chat_id=CHAT_ID,
            email='pai@example.com',
            state_id=STATE_ID,
            context_data={
                'current_responsible': {
                    'relationship': 'father',
                    'name': 'Thiago Tancredi',
                    'phone': '62982551800',
                    'phone_is_whatsapp': True,
                },
            },
        )
    elif runner == 'address_zip_code':
        result = await handler.process_student_address_zip_code_message(
            chat_id=CHAT_ID,
            zip_code='74815705',
            state_id=STATE_ID,
            context_data={},
        )
    elif runner == 'address_street':
        result = await handler.process_student_address_street_message(
            chat_id=CHAT_ID,
            street='Rua Natal',
            state_id=STATE_ID,
            context_data={'address': {'city': 'Goiânia', 'state': 'GO'}},
        )
    elif runner == 'address_neighborhood':
        result = await (
            handler.process_student_address_neighborhood_message(
                chat_id=CHAT_ID,
                neighborhood='Alto da Glória',
                state_id=STATE_ID,
                context_data={'address': {'street': 'Rua Natal'}},
            )
        )
    elif runner == 'address_number':
        result = await handler.process_student_address_number_message(
            chat_id=CHAT_ID,
            number='327',
            state_id=STATE_ID,
            context_data={
                'address': {
                    'street': 'Rua Natal',
                    'neighborhood': 'Alto da Glória',
                },
            },
        )
    else:
        result = await handler.process_student_address_complement_message(
            chat_id=CHAT_ID,
            complement='Casa 2',
            state_id=STATE_ID,
            context_data={
                'address': {
                    'street': 'Rua Natal',
                    'neighborhood': 'Alto da Glória',
                    'number': '327',
                },
            },
        )

    assert result == {'status': 'waiting_student_field_confirmation'}

    pending_field_confirmation = extract_pending_field_confirmation(
        state_service,
    )
    assert pending_field_confirmation['source_step'] == expected_step
    assert pending_field_confirmation['value'] == expected_value
    assert (
        pending_field_confirmation['display_value']
        == expected_display_value
    )


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

    assert result == {'status': 'waiting_student_field_confirmation'}

    state_service.update_student_creation_context.assert_awaited_once()
    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )

    assert update_kwargs['state_id'] == STATE_ID
    assert (
        update_kwargs['next_step']
        == TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION
    )
    pending_field = update_kwargs['context_data']['pending_field_confirmation']
    assert pending_field['source_step'] == TelegramStep.WAITING_STUDENT_DUE_DAY
    assert pending_field['value'] == DUE_DAY
    assert pending_field['display_value'] == f'Dia {DUE_DAY}'

    telegram_service.send_message.assert_awaited_once()
    send_kwargs = telegram_service.send_message.await_args.kwargs

    assert send_kwargs['chat_id'] == CHAT_ID

    summary_text = send_kwargs['text']
    reply_markup = send_kwargs['reply_markup']

    assert 'Confirme o dia de vencimento' in summary_text
    assert f'Dia {DUE_DAY}' in summary_text

    assert reply_markup['inline_keyboard'][0][0] == {
        'text': '✅ Confirmar',
        'callback_data': 'students:create:field:confirm',
    }
    assert reply_markup['inline_keyboard'][1][0] == {
        'text': '✏️ Reescrever',
        'callback_data': 'students:create:field:rewrite',
    }
    assert reply_markup['inline_keyboard'][2][0] == {
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

    assert result == {'status': 'waiting_student_field_confirmation'}

    state_service.update_student_creation_context.assert_awaited_once()
    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )

    assert update_kwargs['state_id'] == STATE_ID
    assert (
        update_kwargs['next_step']
        == TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION
    )
    pending_field = update_kwargs['context_data']['pending_field_confirmation']
    assert pending_field['source_step'] == TelegramStep.WAITING_STUDENT_DUE_DAY
    assert pending_field['value'] == DUE_DAY
    assert pending_field['display_value'] == f'Dia {DUE_DAY}'

    telegram_service.send_message.assert_awaited_once()
    send_kwargs = telegram_service.send_message.await_args.kwargs

    summary_text = send_kwargs['text']
    reply_markup = send_kwargs['reply_markup']

    assert 'Confirme o dia de vencimento' in summary_text
    assert f'Dia {DUE_DAY}' in summary_text

    assert reply_markup['inline_keyboard'][0][0] == {
        'text': '✅ Confirmar',
        'callback_data': 'students:create:field:confirm',
    }
    assert reply_markup['inline_keyboard'][1][0] == {
        'text': '✏️ Reescrever',
        'callback_data': 'students:create:field:rewrite',
    }
    assert reply_markup['inline_keyboard'][2][0] == {
        'text': '❌ Cancelar cadastro',
        'callback_data': 'students:create:cancel',
    }


@pytest.mark.asyncio
async def test_student_name_confirmation_rewrite() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_student_name_message(
        chat_id=CHAT_ID,
        student_name='Narutoo Uzumaki',
        state_id=STATE_ID,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_field_confirmation'}

    pending_context = (
        state_service.update_student_creation_context.await_args.kwargs[
            'context_data'
        ]
    )

    state_service.update_student_creation_context.reset_mock()
    telegram_service.send_message.reset_mock()
    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
        'context_data': pending_context,
    }

    rewrite_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:create:field:rewrite',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert rewrite_result == {'status': 'waiting_student_name'}

    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )
    assert update_kwargs['next_step'] == TelegramStep.WAITING_STUDENT_NAME
    assert update_kwargs['context_data'] == {}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Digite o nome completo do aluno.' in send_kwargs['text']


@pytest.mark.asyncio
async def test_student_name_confirmation_confirm() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    modality_service = AsyncMock()
    modality_service.list_selected_by_academy.return_value = [
        SimpleNamespace(id=1, name='Taekwondo'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=modality_service,
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_student_name_message(
        chat_id=CHAT_ID,
        student_name='Naruto Uzumaki',
        state_id=STATE_ID,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_field_confirmation'}

    pending_context = (
        state_service.update_student_creation_context.await_args.kwargs[
            'context_data'
        ]
    )

    state_service.update_student_creation_context.reset_mock()
    telegram_service.send_message.reset_mock()
    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
        'context_data': pending_context,
    }

    confirm_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:create:field:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_result == {'status': 'waiting_student_modality'}

    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )
    assert update_kwargs['next_step'] == TelegramStep.WAITING_STUDENT_MODALITY
    assert update_kwargs['context_data']['student_name'] == 'Naruto Uzumaki'
    assert (
        'pending_field_confirmation' not in update_kwargs['context_data']
    )

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Agora escolha a modalidade do aluno:' in send_kwargs['text']
    assert send_kwargs['reply_markup']['inline_keyboard'][0][0] == {
        'text': 'Taekwondo',
        'callback_data': 'students:create:modality:1',
    }


@pytest.mark.asyncio
async def test_student_name_confirmation_cancel() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
        'context_data': {
            'pending_field_confirmation': {
                'source_step': TelegramStep.WAITING_STUDENT_NAME,
                'field_label': 'o nome do aluno',
                'value': 'Naruto Uzumaki',
                'display_value': 'Naruto Uzumaki',
                'prompt_text': 'Digite o nome completo do aluno.',
            },
        },
    }

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:create:cancel',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_creation_cancelled'}

    state_service.complete_current_flow.assert_awaited_once_with(STATE_ID)
    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Cadastro de aluno cancelado' in send_kwargs['text']


@pytest.mark.asyncio
async def test_address_reference_search_without_results_shows_actions(
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.search_by_name.return_value = []

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_student_address_reference_search_message(
        chat_id=CHAT_ID,
        search_text='Aluno Inexistente',
        state_id=STATE_ID,
        context_data={'student_name': 'Naruto'},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_address_reference_search_empty'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Não encontrei nenhum aluno com o nome "Aluno Inexistente".' in (
        send_kwargs['text']
    )
    assert 'O que deseja fazer?' in send_kwargs['text']
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '🔎 Pesquisar novamente',
        '🔙 Voltar para opções de endereço',
        '❌ Cancelar cadastro',
    ]


@pytest.mark.asyncio
async def test_address_reference_search_with_results_shows_actions() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.search_by_name.return_value = [
        SimpleNamespace(id=1, name='Lukito Referencia'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_student_address_reference_search_message(
        chat_id=CHAT_ID,
        search_text='Lukito',
        state_id=STATE_ID,
        context_data={'student_name': 'Naruto'},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_address_reference_search_sent'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Encontrei estes alunos.' in send_kwargs['text']
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '🏠 Lukito Referencia',
        '🔎 Pesquisar novamente',
        '🔙 Voltar para opções de endereço',
        '❌ Cancelar cadastro',
    ]


@pytest.mark.asyncio
async def test_address_reference_search_again_keeps_prompt_and_clears_context(
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
        'context_data': {
            'student_name': 'Naruto',
            'address_reference_student_name': 'Lukito Referencia',
            'address_reference_student_id': 1,
            'address_reference': {'street': 'Rua Natal'},
            'address': {'street': 'Rua Antiga'},
        },
    }

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:create:address:search_again',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_address_reference_search'}

    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )
    assert (
        'address_reference_student_name'
        not in update_kwargs['context_data']
    )
    assert 'address_reference_student_id' not in update_kwargs['context_data']
    assert 'address_reference' not in update_kwargs['context_data']
    assert 'address' not in update_kwargs['context_data']

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Digite o nome do aluno que já possui o endereço' in (
        send_kwargs['text']
    )


@pytest.mark.asyncio
async def test_address_reference_back_returns_to_address_options() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
        'context_data': {'student_name': 'Naruto'},
    }

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:create:address:back',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_address_choice'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert send_kwargs['text'] == 'Como deseja informar o endereço do aluno?'
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '🏠 Cadastrar novo endereço',
        '🔁 Usar endereço de outro aluno',
        '⏭️ Pular endereço',
        '❌ Cancelar cadastro',
    ]


@pytest.mark.asyncio
async def test_responsible_reference_search_without_results_shows_actions(
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.search_by_name.return_value = []

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = (
        await handler.process_student_responsible_reference_search_message(
            chat_id=CHAT_ID,
            search_text='Aluno Inexistente',
            state_id=STATE_ID,
            context_data={'student_name': 'Naruto'},
            context=SimpleNamespace(academy_id=ACADEMY_ID),
        )
    )

    assert result == {'status': 'student_responsible_reference_search_empty'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '🔎 Pesquisar novamente',
        '🔙 Voltar para opções de responsável',
        '❌ Cancelar cadastro',
    ]


@pytest.mark.asyncio
async def test_responsible_reference_search_with_results_shows_actions(
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.search_by_name.return_value = [
        SimpleNamespace(id=1, name='Lukito Referencia'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = (
        await handler.process_student_responsible_reference_search_message(
            chat_id=CHAT_ID,
            search_text='Lukito',
            state_id=STATE_ID,
            context_data={'student_name': 'Naruto'},
            context=SimpleNamespace(academy_id=ACADEMY_ID),
        )
    )

    assert result == {'status': 'student_responsible_reference_search_sent'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '🔁 Lukito Referencia',
        '🔎 Pesquisar novamente',
        '🔙 Voltar para opções de responsável',
        '❌ Cancelar cadastro',
    ]


@pytest.mark.asyncio
async def test_responsible_reference_search_again_keeps_prompt() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': (
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH
        ),
        'context_data': {
            'student_name': 'Naruto',
            'responsible_type': 'external',
        },
    }

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:create:responsible:search_again',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_responsible_reference_search'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Digite o nome do aluno que já possui esse mesmo responsável.' in (
        send_kwargs['text']
    )


@pytest.mark.asyncio
async def test_responsible_reference_back_returns_to_options() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': (
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH
        ),
        'context_data': {
            'student_name': 'Naruto',
            'responsible_type': 'external',
        },
    }

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:create:responsible:back',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_responsible_choice'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert (
        send_kwargs['text']
        == 'Como deseja informar o responsável do aluno?'
    )
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '👤 Cadastrar novo responsável',
        '🔁 Usar responsável de outro aluno',
        '❌ Cancelar cadastro',
    ]


@pytest.mark.asyncio
async def test_address_reference_selected_without_address_shows_actions(
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = {
        'student': {'name': 'Lukito Referencia'},
        'address': None,
    }
    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
        'context_data': {'student_name': 'Naruto'},
    }

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler._process_address_reference_selected(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
        callback_data='students:create:address:reference:1',
    )

    assert result == {'status': 'student_address_reference_without_data'}

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert 'Esse aluno não possui endereço cadastrado.' in send_kwargs['text']
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '🔎 Pesquisar novamente',
        '🔙 Voltar para opções de endereço',
        '❌ Cancelar cadastro',
    ]


def test_reused_address_appears_in_summary() -> None:
    context_data = make_self_responsible_context()
    context_data['due_day'] = DUE_DAY
    context_data['address'] = {}
    context_data['address_reference_student_name'] = 'Lukito Referencia'
    context_data['address_reference'] = {
        'zip_code': '74815705',
        'street': 'Rua Natal',
        'neighborhood': 'Alto da Glória',
        'city': 'Goiânia',
        'state': 'GO',
        'number': '327',
        'complement': 'Casa 1',
    }

    summary = StudentsMenuHandler._build_student_summary(context_data)

    assert 'Reutilizado de: Lukito Referencia' in summary
    assert 'Rua Natal' in summary


def test_skip_address_keeps_summary_as_not_informed() -> None:
    context_data = make_self_responsible_context()
    context_data['due_day'] = DUE_DAY
    context_data.pop('address')

    summary = StudentsMenuHandler._build_student_summary(context_data)

    assert '🏠 Endereço\nNão informado' in summary


@pytest.mark.asyncio
async def test_reuse_responsible_and_address_paths_still_work() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': (
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH
        ),
        'context_data': {
            'student_name': 'Irmao do Lukito',
            'modality_id': 1,
            'sex': 'masculino',
            'responsible_type': 'external',
            'responsibles': [],
            'responsible_references': [],
        },
    }
    student_service.get_details.return_value = {
        'student': {'name': 'Lukito Referencia'},
        'responsibles': [
            {
                'id': 10,
                'relationship': 'father',
                'name': 'Pai Referencia',
                'phone': '62911111111',
                'phone_is_whatsapp': True,
                'email': 'pai@example.com',
            },
        ],
    }

    responsible_result = await handler._save_responsible_references(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
        reference_student_id=1,
        selected_responsible_id=10,
    )

    assert responsible_result == {
        'status': 'waiting_student_responsible_next_action'
    }

    responsible_context = (
        state_service.update_student_creation_context.await_args.kwargs[
            'context_data'
        ]
    )
    assert responsible_context['responsible_references'] == [
        {
            'responsible_id': 10,
            'relationship': 'father',
        },
    ]

    state_service.update_student_creation_context.reset_mock()
    telegram_service.send_message.reset_mock()
    state_service.get_by_telegram_user_id.return_value = {
        'id': STATE_ID,
        'current_flow': 'student_creation',
        'current_step': TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
        'context_data': responsible_context,
    }
    student_service.get_details.return_value = {
        'student': {'name': 'Lukito Referencia'},
        'address': {
            'zip_code': '74815705',
            'street': 'Rua Natal',
            'number': '327',
            'complement': 'Casa 1',
            'neighborhood': 'Alto da Gloria',
            'city': 'Goiania',
            'state': 'GO',
        },
    }

    address_result = await handler._process_address_reference_selected(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
        callback_data='students:create:address:reference:1',
    )

    assert address_result == {'status': 'waiting_student_cpf'}

    update_kwargs = (
        state_service.update_student_creation_context.await_args.kwargs
    )
    assert update_kwargs['next_step'] == TelegramStep.WAITING_STUDENT_CPF
    assert update_kwargs['context_data']['address_reference_student_name'] == (
        'Lukito Referencia'
    )
    assert update_kwargs['context_data']['address_reference']['street'] == (
        'Rua Natal'
    )

    assert (
        telegram_service.send_message.await_count
        == EXPECTED_ADDRESS_REUSE_MESSAGES
    )
    last_message = telegram_service.send_message.await_args.kwargs
    assert 'Qual é o CPF do aluno?' in last_message['text']


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
