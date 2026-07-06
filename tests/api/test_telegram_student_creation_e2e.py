from http import HTTPStatus
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.modality import Modality
from dojoflow.services.cep import CepService
from tests.helpers.onboarding import register_onboarding

TELEGRAM_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'
CHAT_ID = 987654321
EXPECTED_RESPONSIBLE_COUNT = 2
EXPECTED_STUDENT_RESPONSIBLE_COUNT = 3
EXPECTED_ADDRESS_COUNT = 1


async def mock_telegram_and_cep(
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

    async def fake_cep_search(
        _self: CepService,
        zip_code: str,
    ) -> Any:
        return SimpleNamespace(
            zip_code=zip_code,
            street='Rua Natal',
            neighborhood='Alto da Glória',
            city='Goiânia',
            state='GO',
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
    monkeypatch.setattr(
        TelegramService,
        'answer_callback_query',
        fake_answer_callback_query,
    )
    monkeypatch.setattr(
        CepService,
        'search',
        fake_cep_search,
    )


async def setup_master_with_modality(
    client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[int, int]:
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

    return payload['telegram_user_id'], modality.id


async def post_text(
    client: AsyncClient,
    secret: str,
    update_id: int,
    telegram_user_id: int,
    text: str,
) -> dict[str, str]:
    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json={
            'update_id': update_id,
            'message': {
                'message_id': update_id,
                'from': {
                    'id': telegram_user_id,
                    'first_name': 'Thiago',
                },
                'chat': {
                    'id': CHAT_ID,
                    'type': 'private',
                },
                'text': text,
            },
        },
    )

    assert response.status_code == HTTPStatus.OK

    return response.json()


async def post_callback(
    client: AsyncClient,
    secret: str,
    update_id: int,
    telegram_user_id: int,
    callback_data: str,
) -> dict[str, str]:
    response = await client.post(
        f'{settings.API_V1_PREFIX}/telegram/webhook',
        headers={
            TELEGRAM_SECRET_HEADER: secret,
        },
        json={
            'update_id': update_id,
            'callback_query': {
                'id': f'callback-{update_id}',
                'from': {
                    'id': telegram_user_id,
                    'first_name': 'Thiago',
                },
                'message': {
                    'chat': {
                        'id': CHAT_ID,
                        'type': 'private',
                    },
                },
                'data': callback_data,
            },
        },
    )

    assert response.status_code == HTTPStatus.OK

    return response.json()


async def post_confirm_field(
    client: AsyncClient,
    secret: str,
    update_id: int,
    telegram_user_id: int,
) -> dict[str, str]:
    return await post_callback(
        client=client,
        secret=secret,
        update_id=update_id,
        telegram_user_id=telegram_user_id,
        callback_data='students:create:field:confirm',
    )


async def post_skip(
    client: AsyncClient,
    secret: str,
    update_id: int,
    telegram_user_id: int,
) -> dict[str, str]:
    return await post_callback(
        client=client,
        secret=secret,
        update_id=update_id,
        telegram_user_id=telegram_user_id,
        callback_data='students:create:skip',
    )


async def enter_and_confirm_field(  # noqa: PLR0913, PLR0917
    client: AsyncClient,
    secret: str,
    text_update_id: int,
    confirm_update_id: int,
    telegram_user_id: int,
    text: str,
    expected_status_after_confirm: str,
) -> None:
    assert await post_text(
        client=client,
        secret=secret,
        update_id=text_update_id,
        telegram_user_id=telegram_user_id,
        text=text,
    ) == {'status': 'waiting_student_field_confirmation'}
    assert await post_confirm_field(
        client=client,
        secret=secret,
        update_id=confirm_update_id,
        telegram_user_id=telegram_user_id,
    ) == {'status': expected_status_after_confirm}


def get_last_student_details_callback(
    sent_messages: list[dict[str, Any]],
) -> str:
    list_message = sent_messages[-1]
    keyboard = list_message['reply_markup']['inline_keyboard']

    return keyboard[0][0]['callback_data']


def find_callback_by_button_text(
    sent_messages: list[dict[str, Any]],
    button_text: str,
) -> str:
    keyboard = sent_messages[-1]['reply_markup']['inline_keyboard']

    for row in keyboard:
        for button in row:
            if button_text in button['text']:
                return button['callback_data']

    raise AssertionError(f'Button not found: {button_text}')


@pytest.mark.asyncio
async def test_e2e_create_student_self_responsible(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []
    answered_callbacks: list[str] = []

    telegram_user_id, modality_id = await setup_master_with_modality(
        client=client,
        db_session=db_session,
    )

    await mock_telegram_and_cep(
        monkeypatch=monkeypatch,
        secret=secret,
        sent_messages=sent_messages,
        answered_callbacks=answered_callbacks,
    )

    assert await post_callback(
        client,
        secret,
        1,
        telegram_user_id,
        'students:create',
    ) == {'status': 'student_creation_started'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2,
        confirm_update_id=21,
        telegram_user_id=telegram_user_id,
        text='Naruto Uzumaki',
        expected_status_after_confirm='waiting_student_modality',
    )
    assert await post_callback(
        client,
        secret,
        3,
        telegram_user_id,
        f'students:create:modality:{modality_id}',
    ) == {'status': 'waiting_student_sex'}
    assert await post_callback(
        client,
        secret,
        4,
        telegram_user_id,
        'students:create:sex:male',
    ) == {'status': 'waiting_student_responsible_type'}
    assert await post_callback(
        client,
        secret,
        5,
        telegram_user_id,
        'students:create:responsible:self',
    ) == {'status': 'waiting_student_phone'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=6,
        confirm_update_id=61,
        telegram_user_id=telegram_user_id,
        text='62999999999',
        expected_status_after_confirm='waiting_student_is_whatsapp',
    )
    assert await post_callback(
        client,
        secret,
        7,
        telegram_user_id,
        'students:create:whatsapp:yes',
    ) == {'status': 'waiting_student_address_choice'}
    assert await post_callback(
        client,
        secret,
        70,
        telegram_user_id,
        'students:create:address:new',
    ) == {'status': 'waiting_student_address_zip_code'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=8,
        confirm_update_id=81,
        telegram_user_id=telegram_user_id,
        text='74815705',
        expected_status_after_confirm='waiting_student_address_number',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=9,
        confirm_update_id=91,
        telegram_user_id=telegram_user_id,
        text='327',
        expected_status_after_confirm='waiting_student_address_complement',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=10,
        confirm_update_id=101,
        telegram_user_id=telegram_user_id,
        text='Casa 2',
        expected_status_after_confirm='waiting_student_cpf',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=11,
        confirm_update_id=111,
        telegram_user_id=telegram_user_id,
        text='12345678911',
        expected_status_after_confirm='waiting_student_instagram',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=12,
        confirm_update_id=121,
        telegram_user_id=telegram_user_id,
        text='NarutoUzumaki',
        expected_status_after_confirm='waiting_student_email',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=13,
        confirm_update_id=131,
        telegram_user_id=telegram_user_id,
        text='naruto@example.com',
        expected_status_after_confirm='waiting_student_birth_date',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=14,
        confirm_update_id=141,
        telegram_user_id=telegram_user_id,
        text='24/01/1994',
        expected_status_after_confirm='waiting_student_monthly_fee',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=15,
        confirm_update_id=151,
        telegram_user_id=telegram_user_id,
        text='250',
        expected_status_after_confirm='waiting_student_due_day',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=16,
        confirm_update_id=161,
        telegram_user_id=telegram_user_id,
        text='7',
        expected_status_after_confirm='waiting_student_confirmation',
    )

    summary_text = sent_messages[-1]['text']

    assert '📋 Resumo do cadastro' in summary_text
    assert 'Nome: Naruto Uzumaki' in summary_text
    assert '📞 Contato' in summary_text
    assert 'Telefone: 62999999999' in summary_text
    assert 'Próprio aluno' in summary_text
    assert '💰 Mensalidade' in summary_text

    assert await post_callback(
        client,
        secret,
        17,
        telegram_user_id,
        'students:create:confirm',
    ) == {'status': 'student_created'}

    assert await post_callback(
        client,
        secret,
        18,
        telegram_user_id,
        'students:list',
    ) == {'status': 'students_list_sent'}

    details_callback = get_last_student_details_callback(sent_messages)

    assert await post_callback(
        client,
        secret,
        19,
        telegram_user_id,
        details_callback,
    ) == {'status': 'student_details_sent'}

    details_text = sent_messages[-1]['text']

    assert '👤 Detalhes do aluno' in details_text
    assert 'Nome: Naruto Uzumaki' in details_text
    assert 'Telefone: 62999999999' in details_text
    assert 'WhatsApp: Sim' in details_text
    assert 'Rua Natal' in details_text
    assert 'Valor: R$ 250.00' in details_text


@pytest.mark.asyncio
async def test_e2e_create_student_external_responsible(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []
    answered_callbacks: list[str] = []

    telegram_user_id, modality_id = await setup_master_with_modality(
        client=client,
        db_session=db_session,
    )

    await mock_telegram_and_cep(
        monkeypatch=monkeypatch,
        secret=secret,
        sent_messages=sent_messages,
        answered_callbacks=answered_callbacks,
    )

    assert await post_callback(
        client,
        secret,
        101,
        telegram_user_id,
        'students:create',
    ) == {'status': 'student_creation_started'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=102,
        confirm_update_id=1021,
        telegram_user_id=telegram_user_id,
        text='Lulu Nuna',
        expected_status_after_confirm='waiting_student_modality',
    )
    assert await post_callback(
        client,
        secret,
        103,
        telegram_user_id,
        f'students:create:modality:{modality_id}',
    ) == {'status': 'waiting_student_sex'}
    assert await post_callback(
        client,
        secret,
        104,
        telegram_user_id,
        'students:create:sex:female',
    ) == {'status': 'waiting_student_responsible_type'}
    assert await post_callback(
        client,
        secret,
        105,
        telegram_user_id,
        'students:create:responsible:external',
    ) == {'status': 'waiting_student_responsible_choice'}
    assert await post_callback(
        client,
        secret,
        1050,
        telegram_user_id,
        'students:create:responsible:new',
    ) == {'status': 'waiting_student_responsible_relationship'}
    assert await post_callback(
        client,
        secret,
        106,
        telegram_user_id,
        'students:create:responsible:relationship:father',
    ) == {'status': 'waiting_student_responsible_name'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=107,
        confirm_update_id=1071,
        telegram_user_id=telegram_user_id,
        text='Thiago Tancredi',
        expected_status_after_confirm='waiting_student_responsible_phone',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=108,
        confirm_update_id=1081,
        telegram_user_id=telegram_user_id,
        text='62982551800',
        expected_status_after_confirm='waiting_student_responsible_is_whatsapp',
    )
    assert await post_callback(
        client,
        secret,
        109,
        telegram_user_id,
        'students:create:responsible:whatsapp:yes',
    ) == {'status': 'waiting_student_responsible_email'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=110,
        confirm_update_id=1101,
        telegram_user_id=telegram_user_id,
        text='pai@example.com',
        expected_status_after_confirm='waiting_student_responsible_next_action',
    )
    assert await post_callback(
        client,
        secret,
        111,
        telegram_user_id,
        'students:create:responsible:continue',
    ) == {'status': 'waiting_student_address_choice'}
    assert await post_callback(
        client,
        secret,
        1110,
        telegram_user_id,
        'students:create:address:new',
    ) == {'status': 'waiting_student_address_zip_code'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=112,
        confirm_update_id=1121,
        telegram_user_id=telegram_user_id,
        text='74815705',
        expected_status_after_confirm='waiting_student_address_number',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=113,
        confirm_update_id=1131,
        telegram_user_id=telegram_user_id,
        text='327',
        expected_status_after_confirm='waiting_student_address_complement',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=114,
        confirm_update_id=1141,
        telegram_user_id=telegram_user_id,
        text='Apartamento 902',
        expected_status_after_confirm='waiting_student_cpf',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=115,
        confirm_update_id=1151,
        telegram_user_id=telegram_user_id,
        text='43256798712',
        expected_status_after_confirm='waiting_student_instagram',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=116,
        confirm_update_id=1161,
        telegram_user_id=telegram_user_id,
        text='LunaNuninha',
        expected_status_after_confirm='waiting_student_email',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=117,
        confirm_update_id=1171,
        telegram_user_id=telegram_user_id,
        text='luna@example.com',
        expected_status_after_confirm='waiting_student_birth_date',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=118,
        confirm_update_id=1181,
        telegram_user_id=telegram_user_id,
        text='24/09/2020',
        expected_status_after_confirm='waiting_student_monthly_fee',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=119,
        confirm_update_id=1191,
        telegram_user_id=telegram_user_id,
        text='350',
        expected_status_after_confirm='waiting_student_due_day',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=120,
        confirm_update_id=1201,
        telegram_user_id=telegram_user_id,
        text='7',
        expected_status_after_confirm='waiting_student_confirmation',
    )

    summary_text = sent_messages[-1]['text']
    family_emoji = '\U0001f468\u200d\U0001f469\u200d\U0001f467'

    assert '📋 Resumo do cadastro' in summary_text
    assert 'Nome: Lulu Nuna' in summary_text
    assert '📞 Contato\nTelefone: Não informado' not in summary_text
    assert f'{family_emoji} Responsáveis' in summary_text
    assert 'Pai: Thiago Tancredi' in summary_text
    assert 'Telefone: 62982551800' in summary_text
    assert '💰 Mensalidade' in summary_text

    assert await post_callback(
        client,
        secret,
        121,
        telegram_user_id,
        'students:create:confirm',
    ) == {'status': 'student_created'}

    assert await post_callback(
        client,
        secret,
        122,
        telegram_user_id,
        'students:list',
    ) == {'status': 'students_list_sent'}

    details_callback = get_last_student_details_callback(sent_messages)

    assert await post_callback(
        client,
        secret,
        123,
        telegram_user_id,
        details_callback,
    ) == {'status': 'student_details_sent'}

    details_text = sent_messages[-1]['text']

    assert '👤 Detalhes do aluno' in details_text
    assert 'Nome: Lulu Nuna' in details_text
    assert 'Rua Natal' in details_text
    assert 'Pai: Thiago Tancredi' in details_text
    assert 'Telefone: 62982551800' in details_text
    assert 'Valor: R$ 350.00' in details_text


@pytest.mark.asyncio
async def test_e2e_create_student_skipping_optional_fields_and_address(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []
    answered_callbacks: list[str] = []

    telegram_user_id, modality_id = await setup_master_with_modality(
        client=client,
        db_session=db_session,
    )

    await mock_telegram_and_cep(
        monkeypatch=monkeypatch,
        secret=secret,
        sent_messages=sent_messages,
        answered_callbacks=answered_callbacks,
    )

    assert await post_callback(
        client,
        secret,
        501,
        telegram_user_id,
        'students:create',
    ) == {'status': 'student_creation_started'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=502,
        confirm_update_id=5021,
        telegram_user_id=telegram_user_id,
        text='Sasuke Uchiha',
        expected_status_after_confirm='waiting_student_modality',
    )
    assert await post_callback(
        client,
        secret,
        503,
        telegram_user_id,
        f'students:create:modality:{modality_id}',
    ) == {'status': 'waiting_student_sex'}
    assert await post_callback(
        client,
        secret,
        504,
        telegram_user_id,
        'students:create:sex:male',
    ) == {'status': 'waiting_student_responsible_type'}
    assert await post_callback(
        client,
        secret,
        505,
        telegram_user_id,
        'students:create:responsible:self',
    ) == {'status': 'waiting_student_phone'}
    assert await post_skip(
        client,
        secret,
        506,
        telegram_user_id,
    ) == {'status': 'waiting_student_address_choice'}
    assert await post_callback(
        client,
        secret,
        507,
        telegram_user_id,
        'students:create:address:skip',
    ) == {'status': 'waiting_student_cpf'}
    assert await post_skip(
        client,
        secret,
        508,
        telegram_user_id,
    ) == {'status': 'waiting_student_instagram'}
    assert await post_skip(
        client,
        secret,
        509,
        telegram_user_id,
    ) == {'status': 'waiting_student_email'}
    assert await post_skip(
        client,
        secret,
        510,
        telegram_user_id,
    ) == {'status': 'waiting_student_birth_date'}
    assert await post_skip(
        client,
        secret,
        511,
        telegram_user_id,
    ) == {'status': 'waiting_student_monthly_fee'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=512,
        confirm_update_id=5121,
        telegram_user_id=telegram_user_id,
        text='180',
        expected_status_after_confirm='waiting_student_due_day',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=513,
        confirm_update_id=5131,
        telegram_user_id=telegram_user_id,
        text='12',
        expected_status_after_confirm='waiting_student_confirmation',
    )

    summary_text = sent_messages[-1]['text']

    assert 'Nome: Sasuke Uchiha' in summary_text
    assert 'Telefone: Não informado' in summary_text
    assert 'WhatsApp: Não informado' in summary_text
    assert 'CPF: Não informado' in summary_text
    assert 'Instagram: Não informado' in summary_text
    assert 'E-mail: Não informado' in summary_text
    assert 'Data de nascimento: Não informado' in summary_text
    assert '🏠 Endereço\nNão informado' in summary_text

    assert await post_callback(
        client,
        secret,
        514,
        telegram_user_id,
        'students:create:confirm',
    ) == {'status': 'student_created'}
    assert await post_callback(
        client,
        secret,
        515,
        telegram_user_id,
        'students:list',
    ) == {'status': 'students_list_sent'}

    details_callback = get_last_student_details_callback(sent_messages)

    assert await post_callback(
        client,
        secret,
        516,
        telegram_user_id,
        details_callback,
    ) == {'status': 'student_details_sent'}

    details_text = sent_messages[-1]['text']
    assert 'Nome: Sasuke Uchiha' in details_text
    assert 'Telefone: Não informado' in details_text
    assert '🏠 Endereço\nNão há endereço cadastrado.' in details_text
    assert 'Valor: R$ 180.00' in details_text


@pytest.mark.asyncio
async def test_e2e_reuse_one_responsible_and_address(  # noqa: PLR0915
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = 'test-secret'
    sent_messages: list[dict[str, Any]] = []
    answered_callbacks: list[str] = []

    telegram_user_id, modality_id = await setup_master_with_modality(
        client=client,
        db_session=db_session,
    )

    await mock_telegram_and_cep(
        monkeypatch=monkeypatch,
        secret=secret,
        sent_messages=sent_messages,
        answered_callbacks=answered_callbacks,
    )

    assert await post_callback(
        client,
        secret,
        1001,
        telegram_user_id,
        'students:create',
    ) == {'status': 'student_creation_started'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1002,
        confirm_update_id=10021,
        telegram_user_id=telegram_user_id,
        text='Lukito Referencia',
        expected_status_after_confirm='waiting_student_modality',
    )
    assert await post_callback(
        client,
        secret,
        1003,
        telegram_user_id,
        f'students:create:modality:{modality_id}',
    ) == {'status': 'waiting_student_sex'}
    assert await post_callback(
        client,
        secret,
        1004,
        telegram_user_id,
        'students:create:sex:male',
    ) == {'status': 'waiting_student_responsible_type'}
    assert await post_callback(
        client,
        secret,
        1005,
        telegram_user_id,
        'students:create:responsible:external',
    ) == {'status': 'waiting_student_responsible_choice'}
    assert await post_callback(
        client,
        secret,
        1006,
        telegram_user_id,
        'students:create:responsible:new',
    ) == {'status': 'waiting_student_responsible_relationship'}
    assert await post_callback(
        client,
        secret,
        1007,
        telegram_user_id,
        'students:create:responsible:relationship:father',
    ) == {'status': 'waiting_student_responsible_name'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1008,
        confirm_update_id=10081,
        telegram_user_id=telegram_user_id,
        text='Pai Referencia',
        expected_status_after_confirm='waiting_student_responsible_phone',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1009,
        confirm_update_id=10091,
        telegram_user_id=telegram_user_id,
        text='62911111111',
        expected_status_after_confirm='waiting_student_responsible_is_whatsapp',
    )
    assert await post_callback(
        client,
        secret,
        1010,
        telegram_user_id,
        'students:create:responsible:whatsapp:yes',
    ) == {'status': 'waiting_student_responsible_email'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1011,
        confirm_update_id=10111,
        telegram_user_id=telegram_user_id,
        text='pai.referencia@example.com',
        expected_status_after_confirm='waiting_student_responsible_next_action',
    )
    assert await post_callback(
        client,
        secret,
        1012,
        telegram_user_id,
        'students:create:responsible:add',
    ) == {'status': 'waiting_student_responsible_relationship'}
    assert await post_callback(
        client,
        secret,
        1013,
        telegram_user_id,
        'students:create:responsible:relationship:mother',
    ) == {'status': 'waiting_student_responsible_name'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1014,
        confirm_update_id=10141,
        telegram_user_id=telegram_user_id,
        text='Mae Referencia',
        expected_status_after_confirm='waiting_student_responsible_phone',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1015,
        confirm_update_id=10151,
        telegram_user_id=telegram_user_id,
        text='62922222222',
        expected_status_after_confirm='waiting_student_responsible_is_whatsapp',
    )
    assert await post_callback(
        client,
        secret,
        1016,
        telegram_user_id,
        'students:create:responsible:whatsapp:no',
    ) == {'status': 'waiting_student_responsible_email'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1017,
        confirm_update_id=10171,
        telegram_user_id=telegram_user_id,
        text='mae.referencia@example.com',
        expected_status_after_confirm='waiting_student_responsible_next_action',
    )
    assert await post_callback(
        client,
        secret,
        1018,
        telegram_user_id,
        'students:create:responsible:continue',
    ) == {'status': 'waiting_student_address_choice'}
    assert await post_callback(
        client,
        secret,
        1019,
        telegram_user_id,
        'students:create:address:new',
    ) == {'status': 'waiting_student_address_zip_code'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1020,
        confirm_update_id=10201,
        telegram_user_id=telegram_user_id,
        text='74815705',
        expected_status_after_confirm='waiting_student_address_number',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1021,
        confirm_update_id=10211,
        telegram_user_id=telegram_user_id,
        text='327',
        expected_status_after_confirm='waiting_student_address_complement',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1022,
        confirm_update_id=10221,
        telegram_user_id=telegram_user_id,
        text='Casa 1',
        expected_status_after_confirm='waiting_student_cpf',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1023,
        confirm_update_id=10231,
        telegram_user_id=telegram_user_id,
        text='11122233344',
        expected_status_after_confirm='waiting_student_instagram',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1024,
        confirm_update_id=10241,
        telegram_user_id=telegram_user_id,
        text='lukito',
        expected_status_after_confirm='waiting_student_email',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1025,
        confirm_update_id=10251,
        telegram_user_id=telegram_user_id,
        text='lukito@example.com',
        expected_status_after_confirm='waiting_student_birth_date',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1026,
        confirm_update_id=10261,
        telegram_user_id=telegram_user_id,
        text='01/01/2018',
        expected_status_after_confirm='waiting_student_monthly_fee',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1027,
        confirm_update_id=10271,
        telegram_user_id=telegram_user_id,
        text='300',
        expected_status_after_confirm='waiting_student_due_day',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=1028,
        confirm_update_id=10281,
        telegram_user_id=telegram_user_id,
        text='10',
        expected_status_after_confirm='waiting_student_confirmation',
    )
    assert await post_callback(
        client,
        secret,
        1029,
        telegram_user_id,
        'students:create:confirm',
    ) == {'status': 'student_created'}

    assert await post_callback(
        client,
        secret,
        2001,
        telegram_user_id,
        'students:create',
    ) == {'status': 'student_creation_started'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2002,
        confirm_update_id=20021,
        telegram_user_id=telegram_user_id,
        text='Irmao do Lukito',
        expected_status_after_confirm='waiting_student_modality',
    )
    assert await post_callback(
        client,
        secret,
        2003,
        telegram_user_id,
        f'students:create:modality:{modality_id}',
    ) == {'status': 'waiting_student_sex'}
    assert await post_callback(
        client,
        secret,
        2004,
        telegram_user_id,
        'students:create:sex:male',
    ) == {'status': 'waiting_student_responsible_type'}
    assert await post_callback(
        client,
        secret,
        2005,
        telegram_user_id,
        'students:create:responsible:external',
    ) == {'status': 'waiting_student_responsible_choice'}
    assert await post_callback(
        client,
        secret,
        2006,
        telegram_user_id,
        'students:create:responsible:reuse',
    ) == {'status': 'waiting_student_responsible_reference_search'}
    assert await post_text(
        client,
        secret,
        2007,
        telegram_user_id,
        'Lukito',
    ) == {'status': 'student_responsible_reference_search_sent'}

    reference_student_callback = find_callback_by_button_text(
        sent_messages,
        'Lukito Referencia',
    )

    assert await post_callback(
        client,
        secret,
        2008,
        telegram_user_id,
        reference_student_callback,
    ) == {'status': 'student_responsible_reference_options_sent'}

    father_callback = find_callback_by_button_text(
        sent_messages,
        'Pai: Pai Referencia',
    )

    assert await post_callback(
        client,
        secret,
        2009,
        telegram_user_id,
        father_callback,
    ) == {'status': 'waiting_student_responsible_next_action'}
    assert await post_callback(
        client,
        secret,
        2010,
        telegram_user_id,
        'students:create:responsible:continue',
    ) == {'status': 'waiting_student_address_choice'}
    assert await post_callback(
        client,
        secret,
        2011,
        telegram_user_id,
        'students:create:address:reuse',
    ) == {'status': 'waiting_student_address_reference_search'}
    assert await post_text(
        client,
        secret,
        2012,
        telegram_user_id,
        'Lukito',
    ) == {'status': 'student_address_reference_search_sent'}

    address_reference_callback = find_callback_by_button_text(
        sent_messages,
        'Lukito Referencia',
    )

    assert await post_callback(
        client,
        secret,
        2013,
        telegram_user_id,
        address_reference_callback,
    ) == {'status': 'waiting_student_cpf'}
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2014,
        confirm_update_id=20141,
        telegram_user_id=telegram_user_id,
        text='55566677788',
        expected_status_after_confirm='waiting_student_instagram',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2015,
        confirm_update_id=20151,
        telegram_user_id=telegram_user_id,
        text='irmaolukito',
        expected_status_after_confirm='waiting_student_email',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2016,
        confirm_update_id=20161,
        telegram_user_id=telegram_user_id,
        text='irmao@example.com',
        expected_status_after_confirm='waiting_student_birth_date',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2017,
        confirm_update_id=20171,
        telegram_user_id=telegram_user_id,
        text='02/02/2019',
        expected_status_after_confirm='waiting_student_monthly_fee',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2018,
        confirm_update_id=20181,
        telegram_user_id=telegram_user_id,
        text='300',
        expected_status_after_confirm='waiting_student_due_day',
    )
    await enter_and_confirm_field(
        client=client,
        secret=secret,
        text_update_id=2019,
        confirm_update_id=20191,
        telegram_user_id=telegram_user_id,
        text='10',
        expected_status_after_confirm='waiting_student_confirmation',
    )

    summary_text = sent_messages[-1]['text']

    assert 'Nome: Irmao do Lukito' in summary_text
    assert 'Reutilizado de: Lukito Referencia' in summary_text
    assert 'Rua Natal' in summary_text
    assert 'Pai: Pai Referencia' in summary_text
    assert 'Mãe: Mae Referencia' not in summary_text

    assert await post_callback(
        client,
        secret,
        2020,
        telegram_user_id,
        'students:create:confirm',
    ) == {'status': 'student_created'}

    responsible_count = await db_session.scalar(
        text('SELECT COUNT(*) FROM responsible')
    )
    student_responsible_count = await db_session.scalar(
        text('SELECT COUNT(*) FROM student_responsible')
    )
    address_count = await db_session.scalar(
        text('SELECT COUNT(*) FROM address')
    )

    assert responsible_count == EXPECTED_RESPONSIBLE_COUNT
    assert student_responsible_count == EXPECTED_STUDENT_RESPONSIBLE_COUNT
    assert address_count == EXPECTED_ADDRESS_COUNT
