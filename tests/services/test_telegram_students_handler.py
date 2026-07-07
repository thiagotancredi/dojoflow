from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from dojoflow.services.telegram_bot.handlers.students import (
    StudentsMenuHandler,
)
from dojoflow.shared.telegram_enums import TelegramFlow, TelegramStep

CHAT_ID = 123
STATE_ID = 10
DUE_DAY = 7
ACADEMY_ID = 99
TELEGRAM_USER_ID = 321
EXPECTED_ADDRESS_REUSE_MESSAGES = 2
UPDATED_DUE_DAY = 15
NAME_EDIT_PROMPT = 'Nome atual:\nThiago\n\nDigite o novo nome do aluno.'
MONTHLY_FEE_EDIT_PROMPT = (
    'Valor atual:\nR$ 250,00\n\nDigite o novo valor da mensalidade.'
)
DUE_DAY_EDIT_PROMPT = (
    'Dia de vencimento atual:\n7\n\nDigite o novo dia de vencimento.'
)
CURRENT_ADDRESS = {
    'zip_code': '74815705',
    'street': 'Rua Natal',
    'number': '327',
    'complement': 'Casa 2',
    'neighborhood': 'Alto da Glória',
    'city': 'Goiânia',
    'state': 'GO',
}
NEW_ADDRESS = {
    'zip_code': '74230110',
    'street': 'Rua Nova',
    'number': '123',
    'complement': '',
    'neighborhood': 'Centro',
    'city': 'Goiânia',
    'state': 'GO',
}
CURRENT_ADDRESS_TEXT = (
    'Logradouro: Rua Natal\n'
    'Número: 327\n'
    'Bairro: Alto da Glória\n'
    'Cidade/Estado: Goiânia/GO\n'
    'CEP: 74815705\n'
    'Complemento: Casa 2'
)
NEW_ADDRESS_TEXT = (
    'Logradouro: Rua Nova\n'
    'Número: 123\n'
    'Bairro: Centro\n'
    'Cidade/Estado: Goiânia/GO\n'
    'CEP: 74230110\n'
    'Complemento: Não informado'
)
CURRENT_RESPONSIBLE = {
    'id': 20,
    'responsible_id': 30,
    'relationship': 'father',
    'name': 'Thiago Tancredi',
    'phone': '62999999999',
    'phone_is_whatsapp': True,
    'email': 'pai@email.com',
}
NEW_RESPONSIBLE = {
    'relationship': 'mother',
    'name': 'Maria Tancredi',
    'phone': '62888888888',
    'phone_is_whatsapp': False,
    'email': 'mae@email.com',
}
CURRENT_RESPONSIBLE_MENU_TEXT = (
    '1. Thiago Tancredi\n'
    '   Parentesco: Pai\n'
    '   Telefone: 62999999999\n'
    '   WhatsApp: Sim\n'
    '   E-mail: pai@email.com'
)


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


def make_student_details(  # noqa: PLR0913
    *,
    student_id: int = 1,
    name: str = 'Thiago',
    modality_name: str = 'Taekwondo',
    sex: str = 'male',
    cpf: str | None = '12345678911',
    instagram: str | None = 'thiago',
    birth_date: str | None = '1990-01-24',
    email: str | None = 'thiago@example.com',
    monthly_fee: str = '250.00',
    due_day: int = 7,
    enrollment_status: str = 'active',
    is_exempt: bool = False,
    address: dict[str, Any] | None = None,
    responsibles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        'student': {
            'id': student_id,
            'name': name,
            'sex': sex,
            'cpf': cpf,
            'instagram': instagram,
            'birth_date': birth_date,
            'email': email,
            'phone': None,
            'phone_is_whatsapp': None,
        },
        'enrollments': [
            {
                'enrollment_id': 10,
                'status': enrollment_status,
                'monthly_fee': monthly_fee,
                'due_day': due_day,
                'is_exempt': is_exempt,
                'modality_name': modality_name,
            }
        ],
        'address': address,
        'responsibles': responsibles or [],
    }


def make_student_edit_state(
    *,
    step: TelegramStep,
    context_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'id': STATE_ID,
        'current_flow': TelegramFlow.STUDENT_EDIT,
        'current_step': step,
        'context_data': {
            'student_id': 1,
            **(context_data or {}),
        },
    }


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
        result = await handler.process_student_address_neighborhood_message(
            chat_id=CHAT_ID,
            neighborhood='Alto da Glória',
            state_id=STATE_ID,
            context_data={'address': {'street': 'Rua Natal'}},
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
        pending_field_confirmation['display_value'] == expected_display_value
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
    assert 'pending_field_confirmation' not in update_kwargs['context_data']

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
async def test_address_reference_search_without_results_shows_actions() -> (
    None
):
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
    assert (
        'Não encontrei nenhum aluno com o nome "Aluno Inexistente".'
        in (send_kwargs['text'])
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
async def test_address_reference_search_again_keeps_prompt_and_clears_context(  # noqa: E501
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
        'address_reference_student_name' not in update_kwargs['context_data']
    )
    assert 'address_reference_student_id' not in update_kwargs['context_data']
    assert 'address_reference' not in update_kwargs['context_data']
    assert 'address' not in update_kwargs['context_data']

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert (
        'Digite o nome do aluno que já possui o endereço'
        in (send_kwargs['text'])
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
async def test_responsible_reference_search_without_results_shows_actions(  # noqa: E501
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
async def test_responsible_reference_search_with_results_shows_actions() -> (
    None
):
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
    assert (
        'Digite o nome do aluno que já possui esse mesmo responsável.'
        in (send_kwargs['text'])
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
        send_kwargs['text'] == 'Como deseja informar o responsável do aluno?'
    )
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '👤 Cadastrar novo responsável',
        '🔁 Usar responsável de outro aluno',
        '❌ Cancelar cadastro',
    ]


@pytest.mark.asyncio
async def test_address_reference_selected_without_address_shows_actions() -> (
    None
):
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


@pytest.mark.asyncio
async def test_student_details_show_edit_button() -> None:
    telegram_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=AsyncMock(),
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler._process_student_details(
        chat_id=CHAT_ID,
        callback_data='students:details:1',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_details_sent'}
    buttons = extract_button_texts(
        telegram_service.send_message.await_args.kwargs['reply_markup']
    )
    assert '✏️ Editar' in buttons


@pytest.mark.asyncio
async def test_open_student_edit_menu_from_details() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:1',
        context=SimpleNamespace(
            academy_id=ACADEMY_ID,
            master_id=22,
        ),
    )

    assert result == {'status': 'waiting_student_edit_menu'}
    state_service.start_student_edit.assert_awaited_once_with(
        telegram_user_id=TELEGRAM_USER_ID,
        academy_id=ACADEMY_ID,
        master_id=22,
        student_id=1,
    )

    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert send_kwargs['text'] == '✏️ Editar aluno\n\nO que deseja editar?'
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '👤 Dados do aluno',
        '🏠 Endereço',
        '👥 Responsáveis',
        '💰 Mensalidade',
        '📌 Status da matrícula',
        '🔙 Voltar aos detalhes',
    ]


@pytest.mark.asyncio
async def test_student_edit_menu_keeps_student_id_in_state() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details()

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:1',
        context=SimpleNamespace(
            academy_id=ACADEMY_ID,
            master_id=22,
        ),
    )

    assert result == {'status': 'waiting_student_edit_menu'}
    state_service.start_student_edit.assert_awaited_once_with(
        telegram_user_id=TELEGRAM_USER_ID,
        academy_id=ACADEMY_ID,
        master_id=22,
        student_id=1,
    )


@pytest.mark.asyncio
async def test_student_edit_section_callback_recovers_missing_state() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details()
    state_service.get_by_telegram_user_id.side_effect = [
        None,
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_MENU,
        ),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:basic:1',
        context=SimpleNamespace(
            academy_id=ACADEMY_ID,
            master_id=22,
        ),
    )

    assert result == {'status': 'waiting_student_edit_basic_data'}
    assert extract_button_texts(
        telegram_service.send_message.await_args_list[-1].kwargs[
            'reply_markup'
        ]
    ) == [
        'Nome',
        'Modalidade',
        'Sexo',
        'CPF',
        'Instagram',
        'Data de nascimento',
        'E-mail',
        '🔙 Voltar para edição',
        '❌ Cancelar edição',
    ]


@pytest.mark.asyncio
async def test_student_edit_basic_data_menu_lists_editable_fields() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=TelegramStep.WAITING_STUDENT_EDIT_MENU)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:basic',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_basic_data'}
    assert extract_button_texts(
        telegram_service.send_message.await_args.kwargs['reply_markup']
    ) == [
        'Nome',
        'Modalidade',
        'Sexo',
        'CPF',
        'Instagram',
        'Data de nascimento',
        'E-mail',
        '🔙 Voltar para edição',
        '❌ Cancelar edição',
    ]


@pytest.mark.asyncio
async def test_student_edit_monthly_fee_menu_lists_editable_fields() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=TelegramStep.WAITING_STUDENT_EDIT_MENU)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:monthly_fee',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_monthly_fee_menu'}
    assert extract_button_texts(
        telegram_service.send_message.await_args.kwargs['reply_markup']
    ) == [
        'Valor da mensalidade',
        'Dia de vencimento',
        '🔙 Voltar para edição',
        '❌ Cancelar edição',
    ]


@pytest.mark.asyncio
async def test_student_edit_enrollment_status_menu_lists_editable_fields() -> (
    None
):
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=TelegramStep.WAITING_STUDENT_EDIT_MENU)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:status',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_enrollment_status_menu'}
    assert extract_button_texts(
        telegram_service.send_message.await_args.kwargs['reply_markup']
    ) == [
        'Isenção da mensalidade',
        'Status da matrícula',
        '🔙 Voltar para edição',
        '❌ Cancelar edição',
    ]


@pytest.mark.asyncio
async def test_student_edit_address_menu_with_current_address_lists_actions(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        address=CURRENT_ADDRESS
    )
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=TelegramStep.WAITING_STUDENT_EDIT_MENU)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:address',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_address_menu'}
    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert CURRENT_ADDRESS_TEXT in send_kwargs['text']
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '📝 Informar novo endereço',
        '🔁 Usar endereço de outro aluno',
        '🧹 Remover endereço',
        '🔙 Voltar para edição',
        '❌ Cancelar edição',
    ]


@pytest.mark.asyncio
async def test_student_edit_address_menu_without_current_address_hides_remove(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        address=None
    )
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=TelegramStep.WAITING_STUDENT_EDIT_MENU)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:address',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_address_menu'}
    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert (
        'Este aluno ainda não possui endereço informado.'
        in (send_kwargs['text'])
    )
    assert '🧹 Remover endereço' not in extract_button_texts(
        send_kwargs['reply_markup']
    )


@pytest.mark.asyncio
async def test_student_edit_responsibles_menu_with_current_responsibles_lists_actions(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        responsibles=[CURRENT_RESPONSIBLE]
    )
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=TelegramStep.WAITING_STUDENT_EDIT_MENU)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:responsibles',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_responsibles_menu'}
    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert CURRENT_RESPONSIBLE_MENU_TEXT in send_kwargs['text']
    assert extract_button_texts(send_kwargs['reply_markup']) == [
        '➕ Adicionar responsável',
        '🔁 Usar responsável de outro aluno',
        '🧹 Remover responsável',
        '🔙 Voltar para edição',
        '❌ Cancelar edição',
    ]


@pytest.mark.asyncio
async def test_student_edit_responsibles_menu_without_current_responsibles_hides_remove(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        responsibles=[]
    )
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=TelegramStep.WAITING_STUDENT_EDIT_MENU)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:section:responsibles',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_responsibles_menu'}
    send_kwargs = telegram_service.send_message.await_args.kwargs
    assert (
        'Este aluno ainda não possui responsável informado.'
        in (send_kwargs['text'])
    )
    assert '🧹 Remover responsável' not in extract_button_texts(
        send_kwargs['reply_markup']
    )


@pytest.mark.asyncio
async def test_student_edit_name_confirm_updates_student_and_returns_details(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(name='Thiago'),
        make_student_details(name='Thiago'),
        make_student_details(name='Tiago'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_BASIC_DATA,
        )
    )

    prompt_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:field:name',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert prompt_result == {'status': 'waiting_student_edit_name'}

    confirm_result = await handler.process_student_edit_name_message(
        chat_id=CHAT_ID,
        student_name='Tiago',
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_result == {'status': 'waiting_student_edit_confirmation'}

    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert pending_edit['current_display'] == 'Thiago'
    assert pending_edit['new_display'] == 'Tiago'

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(
            academy_id=ACADEMY_ID,
            master_id=22,
        ),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_basic_data.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        data={'name': 'Tiago'},
    )
    assert telegram_service.send_message.await_args_list[2].kwargs['text'] == (
        'Alteração salva com sucesso! ✅'
    )
    assert (
        'Nome: Tiago'
        in (telegram_service.send_message.await_args_list[3].kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_name_rewrite_keeps_same_field_and_uses_second_value(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(name='Thiago'),
        make_student_details(name='Thiago'),
        make_student_details(name='Thiago'),
        make_student_details(name='Thiagoo'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    first_confirmation = await handler.process_student_edit_name_message(
        chat_id=CHAT_ID,
        student_name='Tiago',
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert first_confirmation == {
        'status': 'waiting_student_edit_confirmation'
    }

    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    rewrite_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:rewrite',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert rewrite_result == {'status': 'waiting_student_edit_name'}

    second_confirmation = await handler.process_student_edit_name_message(
        chat_id=CHAT_ID,
        student_name='Thiagoo',
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert second_confirmation == {
        'status': 'waiting_student_edit_confirmation'
    }

    second_pending = (
        state_service.update_student_edit_context.await_args.kwargs[
            'context_data'
        ]['pending_student_edit']
    )
    assert second_pending['new_display'] == 'Thiagoo'


@pytest.mark.asyncio
async def test_student_edit_monthly_fee_confirm_updates_enrollment_and_returns_details(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(monthly_fee='250.00'),
        make_student_details(monthly_fee='250.00'),
        make_student_details(monthly_fee='180.00'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE_MENU,
        )
    )

    prompt_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:monthly_fee:monthly_fee',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert prompt_result == {'status': 'waiting_student_edit_monthly_fee'}

    confirm_result = await handler.process_student_edit_monthly_fee_message(
        chat_id=CHAT_ID,
        monthly_fee_text='180,00',
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_result == {'status': 'waiting_student_edit_confirmation'}

    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert pending_edit['value'] == '180.00'
    assert pending_edit['current_display'] == 'R$ 250,00'
    assert pending_edit['new_display'] == 'R$ 180,00'

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_enrollment.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        data={'monthly_fee': '180.00'},
    )
    assert telegram_service.send_message.await_args_list[2].kwargs['text'] == (
        'Alteração salva com sucesso! ✅'
    )
    assert (
        'Valor: R$ 180.00'
        in telegram_service.send_message.await_args_list[3].kwargs['text']
    )


@pytest.mark.asyncio
async def test_student_edit_monthly_fee_rewrite_keeps_same_field_and_uses_second_value(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(monthly_fee='250.00'),
        make_student_details(monthly_fee='250.00'),
        make_student_details(monthly_fee='250.00'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    first_confirmation = (
        await handler.process_student_edit_monthly_fee_message(
            chat_id=CHAT_ID,
            monthly_fee_text='180',
            state_id=STATE_ID,
            context_data={'student_id': 1},
            context=SimpleNamespace(academy_id=ACADEMY_ID),
        )
    )

    assert first_confirmation == {
        'status': 'waiting_student_edit_confirmation'
    }

    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    rewrite_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:rewrite',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert rewrite_result == {'status': 'waiting_student_edit_monthly_fee'}
    assert telegram_service.send_message.await_args.kwargs['text'] == (
        MONTHLY_FEE_EDIT_PROMPT
    )

    second_confirmation = (
        await handler.process_student_edit_monthly_fee_message(
            chat_id=CHAT_ID,
            monthly_fee_text='190.50',
            state_id=STATE_ID,
            context_data={'student_id': 1},
            context=SimpleNamespace(academy_id=ACADEMY_ID),
        )
    )

    assert second_confirmation == {
        'status': 'waiting_student_edit_confirmation'
    }

    second_pending = (
        state_service.update_student_edit_context.await_args.kwargs[
            'context_data'
        ]['pending_student_edit']
    )
    assert second_pending['new_display'] == 'R$ 190,50'


@pytest.mark.asyncio
@pytest.mark.parametrize('monthly_fee_text', ['abc', '0'])
async def test_student_edit_monthly_fee_invalid_value_keeps_same_field(
    monthly_fee_text: str,
) -> None:
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

    result = await handler.process_student_edit_monthly_fee_message(
        chat_id=CHAT_ID,
        monthly_fee_text=monthly_fee_text,
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'invalid_student_edit_monthly_fee'}
    state_service.update_student_edit_context.assert_not_awaited()
    student_service.update_enrollment.assert_not_awaited()
    assert (
        'Valor de mensalidade inválido.'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_due_day_confirm_updates_enrollment_and_returns_details(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(due_day=7),
        make_student_details(due_day=UPDATED_DUE_DAY),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    confirm_result = await handler.process_student_edit_due_day_message(
        chat_id=CHAT_ID,
        due_day_text=str(UPDATED_DUE_DAY),
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_result == {'status': 'waiting_student_edit_confirmation'}

    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert pending_edit['value'] == UPDATED_DUE_DAY
    assert pending_edit['current_display'] == '7'
    assert pending_edit['new_display'] == str(UPDATED_DUE_DAY)

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_enrollment.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        data={'due_day': UPDATED_DUE_DAY},
    )
    assert (
        f'Vencimento: dia {UPDATED_DUE_DAY}'
        in telegram_service.send_message.await_args_list[2].kwargs['text']
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('due_day_text', ['0', '29', 'abc'])
async def test_student_edit_due_day_invalid_value_keeps_same_field(
    due_day_text: str,
) -> None:
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

    result = await handler.process_student_edit_due_day_message(
        chat_id=CHAT_ID,
        due_day_text=due_day_text,
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'invalid_student_edit_due_day'}
    state_service.update_student_edit_context.assert_not_awaited()
    student_service.update_enrollment.assert_not_awaited()
    assert (
        'Dia de vencimento inválido.'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_monthly_fee_cancel_returns_to_details_without_changes(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        monthly_fee='250.00'
    )
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
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
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:cancel',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_edit_cancelled'}
    student_service.update_enrollment.assert_not_awaited()
    assert (
        'Valor: R$ 250.00'
        in telegram_service.send_message.await_args.kwargs['text']
    )


@pytest.mark.asyncio
async def test_student_edit_is_exempt_confirm_updates_enrollment_and_returns_details(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(is_exempt=False),
        make_student_details(is_exempt=False),
        make_student_details(is_exempt=True),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ENROLLMENT_STATUS_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    prompt_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:status:is_exempt',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert prompt_result == {'status': 'waiting_student_edit_is_exempt'}
    assert (
        'Isenção atual:\nNão'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_IS_EXEMPT
        )
    )

    confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:status:is_exempt:yes',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirmation == {'status': 'waiting_student_edit_confirmation'}
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert (
        'Confirmar alteração de isenção?' in pending_edit['confirmation_text']
    )
    assert 'De:\nNão' in pending_edit['confirmation_text']
    assert 'Para:\nSim' in pending_edit['confirmation_text']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={'pending_student_edit': pending_edit},
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_enrollment.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        data={'is_exempt': True},
    )
    assert (
        'Isento: Sim'
        in (telegram_service.send_message.await_args_list[-1].kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_enrollment_status_confirm_updates_and_returns_details(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(enrollment_status='active'),
        make_student_details(enrollment_status='active'),
        make_student_details(enrollment_status='inactive'),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ENROLLMENT_STATUS_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    prompt_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:status:status',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert prompt_result == {
        'status': 'waiting_student_edit_enrollment_status'
    }
    assert (
        'Status atual:\nAtiva'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ENROLLMENT_STATUS
        )
    )

    confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:status:enrollment:inactive',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirmation == {'status': 'waiting_student_edit_confirmation'}
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert (
        'Confirmar alteração de status?' in pending_edit['confirmation_text']
    )
    assert 'De:\nAtiva' in pending_edit['confirmation_text']
    assert 'Para:\nInativa' in pending_edit['confirmation_text']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={'pending_student_edit': pending_edit},
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_enrollment.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        data={'status': 'inactive'},
    )
    assert (
        'Status: Inativa'
        in (telegram_service.send_message.await_args_list[-1].kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_is_exempt_cancel_returns_to_details_without_changes(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        is_exempt=False
    )
    state_service.get_by_telegram_user_id.return_value = (  # noqa: E501
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': {
                    'action': 'update_enrollment',
                    'source_step': (
                        TelegramStep.WAITING_STUDENT_EDIT_IS_EXEMPT.value
                    ),
                    'field': 'is_exempt',
                    'value': True,
                    'prompt_text': (
                        'Isenção atual:\nNão\n\nDeseja alterar para:'
                    ),
                    'prompt_reply_markup': {'inline_keyboard': []},
                    'confirmation_text': (
                        'Confirmar alteração de isenção?\n\n'
                        'De:\nNão\n\nPara:\nSim'
                    ),
                    'include_rewrite': False,
                    'confirm_label': '✅ Confirmar alteração',
                },
            },
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:cancel',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_edit_cancelled'}
    student_service.update_enrollment.assert_not_awaited()
    assert (
        'Isento: Não'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_back_from_enrollment_status_confirmation_returns_to_menu(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (  # noqa: E501
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': {
                    'action': 'update_enrollment',
                    'source_step': (
                        TelegramStep.WAITING_STUDENT_EDIT_IS_EXEMPT.value
                    ),
                    'field': 'is_exempt',
                    'value': True,
                    'prompt_text': (
                        'Isenção atual:\nNão\n\nDeseja alterar para:'
                    ),
                    'prompt_reply_markup': {'inline_keyboard': []},
                    'confirmation_text': (
                        'Confirmar alteração de isenção?\n\n'
                        'De:\nNão\n\nPara:\nSim'
                    ),
                    'include_rewrite': False,
                    'confirm_label': '✅ Confirmar alteração',
                },
            },
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:back',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_enrollment_status_menu'}
    assert extract_button_texts(
        telegram_service.send_message.await_args.kwargs['reply_markup']
    ) == [
        'Isenção da mensalidade',
        'Status da matrícula',
        '🔙 Voltar para edição',
        '❌ Cancelar edição',
    ]


@pytest.mark.asyncio
async def test_student_edit_new_address_flow_confirms_and_saves(  # noqa: PLR0914
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    cep_service = AsyncMock()
    cep_service.search.return_value = SimpleNamespace(
        zip_code=NEW_ADDRESS['zip_code'],
        street=NEW_ADDRESS['street'],
        neighborhood=NEW_ADDRESS['neighborhood'],
        city=NEW_ADDRESS['city'],
        state=NEW_ADDRESS['state'],
    )
    student_service.get_details.side_effect = [
        make_student_details(address=CURRENT_ADDRESS),
        make_student_details(address=NEW_ADDRESS),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=cep_service,
    )

    start_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:address:new',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert start_result == {'status': 'waiting_student_edit_address_zip_code'}

    zip_result = await handler.process_student_edit_address_zip_code_message(
        chat_id=CHAT_ID,
        zip_code=NEW_ADDRESS['zip_code'],
        state_id=STATE_ID,
        context_data={
            'student_id': 1,
            'edit_current_address': CURRENT_ADDRESS,
        },
    )

    assert zip_result == {'status': 'waiting_student_edit_field_confirmation'}
    pending_field = (
        state_service.update_student_edit_context.await_args.kwargs[
            'context_data'
        ]['pending_student_edit_field_confirmation']
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_FIELD_CONFIRMATION,
            context_data={
                'edit_current_address': CURRENT_ADDRESS,
                'pending_student_edit_field_confirmation': pending_field,
            },
        )
    )

    confirm_zip = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:field:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_zip == {'status': 'waiting_student_edit_address_number'}

    number_result = await handler.process_student_edit_address_number_message(
        chat_id=CHAT_ID,
        number=NEW_ADDRESS['number'],
        state_id=STATE_ID,
        context_data={
            'student_id': 1,
            'edit_current_address': CURRENT_ADDRESS,
            'edit_address': {
                'zip_code': NEW_ADDRESS['zip_code'],
                'street': NEW_ADDRESS['street'],
                'neighborhood': NEW_ADDRESS['neighborhood'],
                'city': NEW_ADDRESS['city'],
                'state': NEW_ADDRESS['state'],
            },
        },
    )

    assert number_result == {
        'status': 'waiting_student_edit_field_confirmation'
    }
    pending_number = (
        state_service.update_student_edit_context.await_args.kwargs[
            'context_data'
        ]['pending_student_edit_field_confirmation']
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_FIELD_CONFIRMATION,
            context_data={
                'edit_current_address': CURRENT_ADDRESS,
                'edit_address': {
                    'zip_code': NEW_ADDRESS['zip_code'],
                    'street': NEW_ADDRESS['street'],
                    'neighborhood': NEW_ADDRESS['neighborhood'],
                    'city': NEW_ADDRESS['city'],
                    'state': NEW_ADDRESS['state'],
                },
                'pending_student_edit_field_confirmation': pending_number,
            },
        )
    )

    confirm_number = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:field:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_number == {
        'status': 'waiting_student_edit_address_complement'
    }

    complement_result = (
        await handler.process_student_edit_address_complement_message(
            chat_id=CHAT_ID,
            complement='',
            state_id=STATE_ID,
            context_data={
                'student_id': 1,
                'edit_current_address': CURRENT_ADDRESS,
                'edit_address': {
                    'zip_code': NEW_ADDRESS['zip_code'],
                    'street': NEW_ADDRESS['street'],
                    'neighborhood': NEW_ADDRESS['neighborhood'],
                    'city': NEW_ADDRESS['city'],
                    'state': NEW_ADDRESS['state'],
                    'number': NEW_ADDRESS['number'],
                },
            },
        )
    )

    assert complement_result == {
        'status': 'waiting_student_edit_field_confirmation'
    }
    pending_complement = (
        state_service.update_student_edit_context.await_args.kwargs[
            'context_data'
        ]['pending_student_edit_field_confirmation']
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_FIELD_CONFIRMATION,
            context_data={
                'edit_current_address': CURRENT_ADDRESS,
                'edit_address': {
                    'zip_code': NEW_ADDRESS['zip_code'],
                    'street': NEW_ADDRESS['street'],
                    'neighborhood': NEW_ADDRESS['neighborhood'],
                    'city': NEW_ADDRESS['city'],
                    'state': NEW_ADDRESS['state'],
                    'number': NEW_ADDRESS['number'],
                },
                'pending_student_edit_field_confirmation': pending_complement,
            },
        )
    )

    final_confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:field:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert final_confirmation == {
        'status': 'waiting_student_edit_confirmation'
    }
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert 'Confirmar novo endereço?' in pending_edit['confirmation_text']
    assert CURRENT_ADDRESS_TEXT in pending_edit['confirmation_text']
    assert NEW_ADDRESS_TEXT in pending_edit['confirmation_text']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'edit_current_address': CURRENT_ADDRESS,
                'edit_address': NEW_ADDRESS,
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_address.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        address_data=NEW_ADDRESS,
    )
    assert (
        'Logradouro: Rua Nova'
        in (telegram_service.send_message.await_args_list[-1].kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_new_address_rewrite_restarts_from_zip_code() -> (
    None
):
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (  # noqa: E501
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'edit_current_address': CURRENT_ADDRESS,
                'edit_address': NEW_ADDRESS,
                'pending_student_edit': {
                    'action': 'update_address',
                    'source_step': (
                        TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE.value
                    ),
                    'prompt_text': (
                        'Digite o CEP do novo endereço.\n\n'
                        'Digite apenas os números.\n\n'
                        'Exemplo:\n'
                        '74230110'
                    ),
                    'prompt_reply_markup': {'inline_keyboard': []},
                    'confirmation_text': 'Confirmar novo endereço?',
                    'include_rewrite': True,
                    'confirm_label': '✅ Confirmar alteração',
                    'rewrite_label': '✏️ Reescrever endereço',
                },
            },
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:rewrite',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_address_zip_code'}
    assert (
        'Digite o CEP do novo endereço.'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_address_reference_search_and_confirm_save() -> (
    None
):
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.search_by_name.return_value = [
        SimpleNamespace(id=2, name='Luna'),
    ]
    student_service.get_details.side_effect = [
        make_student_details(address=CURRENT_ADDRESS),
        make_student_details(student_id=2, name='Luna', address=NEW_ADDRESS),
        make_student_details(address=NEW_ADDRESS),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    search_prompt = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:address:reuse',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert search_prompt == {
        'status': 'waiting_student_edit_address_reference_search'
    }

    search_result = (
        await handler.process_student_edit_address_reference_search_message(
            chat_id=CHAT_ID,
            search_text='Luna',
            state_id=STATE_ID,
            context_data={'student_id': 1},
            context=SimpleNamespace(academy_id=ACADEMY_ID),
        )
    )

    assert search_result == {
        'status': 'student_edit_address_reference_search_sent'
    }

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_REFERENCE_SEARCH
        )
    )

    confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:address:reference:2',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirmation == {'status': 'waiting_student_edit_confirmation'}
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert 'Confirmar uso deste endereço?' in pending_edit['confirmation_text']
    assert 'Aluno selecionado:\nLuna' in pending_edit['confirmation_text']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'edit_address_reference_student_id': 2,
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved == {'status': 'student_edit_saved'}
    student_service.reuse_address.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        reference_student_id=2,
    )


@pytest.mark.asyncio
async def test_student_edit_address_reference_without_address_shows_actions(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(address=CURRENT_ADDRESS),
        make_student_details(student_id=2, name='Luna', address=None),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_REFERENCE_SEARCH
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:address:reference:2',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_edit_address_reference_without_data'}
    assert (
        'Esse aluno não possui endereço cadastrado.'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_remove_address_confirm_saves() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(address=CURRENT_ADDRESS),
        make_student_details(address=None),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:address:remove',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirmation == {'status': 'waiting_student_edit_confirmation'}
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert (
        'Confirmar remoção do endereço?' in (pending_edit['confirmation_text'])
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved == {'status': 'student_edit_saved'}
    student_service.remove_address.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
    )


@pytest.mark.asyncio
async def test_student_edit_new_responsible_flow_confirms_and_saves(  # noqa: PLR0914
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(name='Thiago'),
        make_student_details(
            responsibles=[
                {
                    'id': 21,
                    'responsible_id': 31,
                    **NEW_RESPONSIBLE,
                },
            ]
        ),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLES_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    start_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:new',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert start_result == {
        'status': 'waiting_student_edit_responsible_relationship'
    }

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_RELATIONSHIP
        )
    )

    relationship_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:relationship:mother',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert relationship_result == {
        'status': 'waiting_student_edit_responsible_name'
    }

    name_result = await handler.process_student_edit_responsible_name_message(
        chat_id=CHAT_ID,
        responsible_name=NEW_RESPONSIBLE['name'],
        state_id=STATE_ID,
        context_data={
            'student_id': 1,
            'edit_responsible': {'relationship': 'mother'},
        },
    )

    assert name_result == {'status': 'waiting_student_edit_field_confirmation'}
    pending_name = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit_field_confirmation']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_FIELD_CONFIRMATION,
            context_data={
                'edit_responsible': {'relationship': 'mother'},
                'pending_student_edit_field_confirmation': pending_name,
            },
        )
    )

    confirm_name = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:field:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_name == {'status': 'waiting_student_edit_responsible_phone'}

    phone_result = (
        await handler.process_student_edit_responsible_phone_message(
            chat_id=CHAT_ID,
            phone=NEW_RESPONSIBLE['phone'],
            state_id=STATE_ID,
            context_data={
                'student_id': 1,
                'edit_responsible': {
                    'relationship': 'mother',
                    'name': NEW_RESPONSIBLE['name'],
                },
            },
        )
    )

    assert phone_result == {
        'status': 'waiting_student_edit_field_confirmation'
    }
    pending_phone = (
        state_service.update_student_edit_context.await_args.kwargs[
            'context_data'
        ]['pending_student_edit_field_confirmation']
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_FIELD_CONFIRMATION,
            context_data={
                'edit_responsible': {
                    'relationship': 'mother',
                    'name': NEW_RESPONSIBLE['name'],
                },
                'pending_student_edit_field_confirmation': pending_phone,
            },
        )
    )

    confirm_phone = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:field:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_phone == {
        'status': 'waiting_student_edit_responsible_is_whatsapp'
    }

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_IS_WHATSAPP,
            context_data={
                'edit_responsible': {
                    'relationship': 'mother',
                    'name': NEW_RESPONSIBLE['name'],
                    'phone': NEW_RESPONSIBLE['phone'],
                },
            },
        )
    )

    whatsapp_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:whatsapp:no',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert whatsapp_result == {
        'status': 'waiting_student_edit_responsible_email'
    }

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_EMAIL,
            context_data={
                'edit_responsible': {
                    **NEW_RESPONSIBLE,
                },
            },
        )
    )

    final_confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:skip_email',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert final_confirmation == {
        'status': 'waiting_student_edit_confirmation'
    }
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert 'Confirmar novo responsável?' in pending_edit['confirmation_text']
    assert 'Aluno:\nThiago' in pending_edit['confirmation_text']
    assert 'Nome: Maria Tancredi' in pending_edit['confirmation_text']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'edit_responsible': {
                    **NEW_RESPONSIBLE,
                },
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.add_responsible.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        responsible_data=NEW_RESPONSIBLE,
    )
    assert (
        'Maria Tancredi'
        in (telegram_service.send_message.await_args_list[-1].kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_new_responsible_rewrite_restarts_from_relationship(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (  # noqa: E501
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'edit_responsible': NEW_RESPONSIBLE,
                'pending_student_edit': {
                    'action': 'add_responsible',
                    'source_step': (
                        TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_RELATIONSHIP.value
                    ),
                    'prompt_text': (
                        '👥 Responsável\n\n'
                        'Qual é o parentesco do responsável com o aluno?'
                    ),
                    'prompt_reply_markup': {'inline_keyboard': []},
                    'confirmation_text': 'Confirmar novo responsável?',
                    'include_rewrite': True,
                    'confirm_label': '✅ Confirmar alteração',
                    'rewrite_label': '✏️ Reescrever responsável',
                },
            },
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:rewrite',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {
        'status': 'waiting_student_edit_responsible_relationship'
    }
    assert (
        'Qual é o parentesco do responsável com o aluno?'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_responsible_reference_search_and_confirm_save(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.search_by_name.return_value = [
        SimpleNamespace(id=2, name='Luna'),
    ]
    student_service.get_details.side_effect = [
        make_student_details(
            student_id=2,
            name='Luna',
            responsibles=[CURRENT_RESPONSIBLE],
        ),
        make_student_details(name='Thiago'),
        make_student_details(responsibles=[CURRENT_RESPONSIBLE]),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLES_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    search_prompt = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:reuse',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert search_prompt == {
        'status': 'waiting_student_edit_responsible_reference_search'
    }

    search_result = await (
        handler.process_student_edit_responsible_reference_search_message(
            chat_id=CHAT_ID,
            search_text='Luna',
            state_id=STATE_ID,
            context_data={'student_id': 1},
            context=SimpleNamespace(academy_id=ACADEMY_ID),
        )
    )

    assert search_result == {
        'status': 'student_edit_responsible_reference_search_sent'
    }

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_REFERENCE_SEARCH
        )
    )

    options_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:reference_student:2',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert options_result == {
        'status': 'student_edit_responsible_reference_options_sent'
    }

    state_service.get_by_telegram_user_id.return_value = (  # noqa: E501
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_REFERENCE_SEARCH,
            context_data={
                'edit_responsible_reference_student_id': 2,
                'edit_responsible_reference_student_name': 'Luna',
                'edit_responsible_reference_details': [CURRENT_RESPONSIBLE],
            },
        )
    )

    confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:reference_responsible:2:30',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirmation == {'status': 'waiting_student_edit_confirmation'}
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert (
        'Confirmar uso deste responsável?'
        in (pending_edit['confirmation_text'])
    )
    assert 'Aluno selecionado:\nLuna' in pending_edit['confirmation_text']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'edit_responsible_reference_details': CURRENT_RESPONSIBLE,
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.reuse_responsible.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        responsible_id=30,
        relationship='father',
    )


@pytest.mark.asyncio
async def test_student_edit_responsible_reference_without_data_shows_actions(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        student_id=2,
        name='Luna',
        responsibles=[],
    )
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_REFERENCE_SEARCH
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:reference_student:2',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {
        'status': 'student_edit_responsible_reference_without_data'
    }
    assert (
        'Esse aluno não possui responsável cadastrado.'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
async def test_student_edit_remove_responsible_confirm_saves() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(responsibles=[CURRENT_RESPONSIBLE]),
        make_student_details(responsibles=[CURRENT_RESPONSIBLE]),
        make_student_details(responsibles=[]),
    ]
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLES_MENU
        )
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    remove_menu = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:remove',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert remove_menu == {
        'status': 'waiting_student_edit_responsible_remove_selection'
    }

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_RESPONSIBLE_REMOVE_SELECTION
        )
    )

    confirmation = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:responsibles:remove_select:20',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirmation == {'status': 'waiting_student_edit_confirmation'}
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert (
        'Confirmar remoção do responsável?'
        in (pending_edit['confirmation_text'])
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'edit_responsible_to_remove': {
                    'student_responsible_id': 20,
                    'name': 'Thiago Tancredi',
                },
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.remove_responsible_link.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        student_responsible_id=20,
    )


@pytest.mark.asyncio
async def test_student_edit_cancel_returns_to_details_without_changes() -> (
    None
):
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.return_value = make_student_details(
        name='Thiago'
    )
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': {
                    'action': 'update',
                    'source_step': (
                        TelegramStep.WAITING_STUDENT_EDIT_NAME.value
                    ),
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
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:cancel',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'student_edit_cancelled'}
    student_service.update_basic_data.assert_not_awaited()
    state_service.complete_current_flow.assert_awaited_once_with(STATE_ID)
    assert (
        'Nome: Thiago'
        in (telegram_service.send_message.await_args.kwargs['text'])
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('step', 'callback_data', 'expected_text'),
    [
        (
            TelegramStep.WAITING_STUDENT_EDIT_NAME,
            'students:edit:back',
            '👤 Dados do aluno',
        ),
        (
            TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE,
            'students:edit:back',
            '💰 Mensalidade',
        ),
        (
            TelegramStep.WAITING_STUDENT_EDIT_BASIC_DATA,
            'students:edit:back:menu',
            '✏️ Editar aluno',
        ),
        (
            TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE_MENU,
            'students:edit:back:menu',
            '✏️ Editar aluno',
        ),
    ],
)
async def test_student_edit_back_returns_to_previous_menu(
    step: TelegramStep,
    callback_data: str,
    expected_text: str,
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(step=step)
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data=callback_data,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert (
        expected_text
        in telegram_service.send_message.await_args.kwargs['text']
    )


@pytest.mark.asyncio
async def test_student_edit_back_from_monthly_fee_confirmation_returns_to_monthly_fee_menu(  # noqa: E501
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
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
    )

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=AsyncMock(),
        cep_service=AsyncMock(),
    )

    result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:back',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert result == {'status': 'waiting_student_edit_monthly_fee_menu'}
    assert telegram_service.send_message.await_args.kwargs['text'] == (
        '💰 Mensalidade\n\nEscolha o campo que deseja editar:'
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        'field',
        'step',
        'message_value',
        'expected_value',
        'expected_display',
        'remove_callback',
        'prompt_fragment',
    ),
    [
        (
            'cpf',
            TelegramStep.WAITING_STUDENT_EDIT_CPF,
            '12345678911',
            '12345678911',
            '123.***.***-11',
            'students:edit:remove:cpf',
            'Digite o novo CPF do aluno.',
        ),
        (
            'instagram',
            TelegramStep.WAITING_STUDENT_EDIT_INSTAGRAM,
            '@thiago',
            'thiago',
            '@thiago',
            'students:edit:remove:instagram',
            'Digite o novo Instagram do aluno.',
        ),
        (
            'birth_date',
            TelegramStep.WAITING_STUDENT_EDIT_BIRTH_DATE,
            '24/01/1994',
            '1994-01-24',
            '24/01/1994',
            'students:edit:remove:birth_date',
            'Digite a nova data de nascimento do aluno.',
        ),
        (
            'email',
            TelegramStep.WAITING_STUDENT_EDIT_EMAIL,
            'novo@example.com',
            'novo@example.com',
            'novo@example.com',
            'students:edit:remove:email',
            'Digite o novo e-mail do aluno.',
        ),
    ],
)
async def test_student_edit_optional_fields_update_and_remove(  # noqa: PLR0913, PLR0917
    field: str,
    step: TelegramStep,
    message_value: str,
    expected_value: str,
    expected_display: str,
    remove_callback: str,
    prompt_fragment: str,
) -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(),
        make_student_details(),
        make_student_details(),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    message_handlers = {
        'cpf': handler.process_student_edit_cpf_message,
        'instagram': handler.process_student_edit_instagram_message,
        'birth_date': handler.process_student_edit_birth_date_message,
        'email': handler.process_student_edit_email_message,
    }

    kwargs_by_field = {
        'cpf': {'cpf': message_value},
        'instagram': {'instagram': message_value},
        'birth_date': {'birth_date_text': message_value},
        'email': {'email': message_value},
    }

    confirm_result = await message_handlers[field](
        chat_id=CHAT_ID,
        state_id=STATE_ID,
        context_data={'student_id': 1},
        context=SimpleNamespace(academy_id=ACADEMY_ID),
        **kwargs_by_field[field],
    )

    assert confirm_result == {'status': 'waiting_student_edit_confirmation'}
    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert pending_edit['value'] == expected_value
    assert pending_edit['new_display'] == expected_display
    assert prompt_fragment in pending_edit['prompt_text']

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=step,
        )
    )

    remove_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data=remove_callback,
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert remove_result == {'status': 'waiting_student_edit_confirmation'}

    removal_pending = (
        state_service.update_student_edit_context.await_args.kwargs[
            'context_data'
        ]['pending_student_edit']
    )
    assert removal_pending['action'] == 'remove'
    assert removal_pending['field'] == field

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': removal_pending,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_basic_data.assert_awaited()
    assert student_service.update_basic_data.await_args.kwargs['data'] == {
        field: None,
    }


@pytest.mark.asyncio
async def test_student_edit_modality_flow_confirms_before_saving() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    modality_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(modality_name='Taekwondo'),
        make_student_details(modality_name='Taekwondo'),
        make_student_details(modality_name='Jiu-jitsu'),
    ]
    modality_service.list_selected_by_academy.return_value = [
        SimpleNamespace(id=1, name='Taekwondo'),
        SimpleNamespace(id=2, name='Jiu-jitsu'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=modality_service,
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_BASIC_DATA,
        )
    )

    prompt_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:field:modality',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert prompt_result == {'status': 'waiting_student_edit_modality'}

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_MODALITY,
        )
    )

    confirm_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:modality:2',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_result == {'status': 'waiting_student_edit_confirmation'}

    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert pending_edit['current_display'] == 'Taekwondo'
    assert pending_edit['new_display'] == 'Jiu-jitsu'

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_modality.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        modality_id=2,
    )


@pytest.mark.asyncio
async def test_student_edit_sex_flow_confirms_before_saving() -> None:
    telegram_service = AsyncMock()
    state_service = AsyncMock()
    student_service = AsyncMock()
    student_service.get_details.side_effect = [
        make_student_details(sex='male'),
        make_student_details(sex='female'),
    ]

    handler = StudentsMenuHandler(
        telegram_service=telegram_service,
        telegram_conversation_state_service=state_service,
        modality_service=AsyncMock(),
        student_service=student_service,
        cep_service=AsyncMock(),
    )

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_SEX,
        )
    )

    confirm_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:sex:female',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert confirm_result == {'status': 'waiting_student_edit_confirmation'}

    pending_edit = state_service.update_student_edit_context.await_args.kwargs[
        'context_data'
    ]['pending_student_edit']
    assert pending_edit['current_display'] == 'Masculino'
    assert pending_edit['new_display'] == 'Feminino'

    state_service.get_by_telegram_user_id.return_value = (
        make_student_edit_state(
            step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data={
                'pending_student_edit': pending_edit,
            },
        )
    )

    saved_result = await handler.process_callback(
        chat_id=CHAT_ID,
        telegram_user_id=TELEGRAM_USER_ID,
        callback_data='students:edit:confirm',
        context=SimpleNamespace(academy_id=ACADEMY_ID),
    )

    assert saved_result == {'status': 'student_edit_saved'}
    student_service.update_basic_data.assert_awaited_once_with(
        academy_id=ACADEMY_ID,
        student_id=1,
        data={'sex': 'female'},
    )
