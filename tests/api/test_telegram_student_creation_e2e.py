from http import HTTPStatus
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.modality import Modality
from dojoflow.services.cep import CepService
from tests.helpers.onboarding import register_onboarding

TELEGRAM_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'
CHAT_ID = 987654321


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


def get_last_student_details_callback(
    sent_messages: list[dict[str, Any]],
) -> str:
    list_message = sent_messages[-1]
    keyboard = list_message['reply_markup']['inline_keyboard']

    return keyboard[0][0]['callback_data']


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
    assert await post_text(
        client,
        secret,
        2,
        telegram_user_id,
        'Naruto Uzumaki',
    ) == {'status': 'waiting_student_modality'}
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
    assert await post_text(
        client,
        secret,
        6,
        telegram_user_id,
        '62999999999',
    ) == {'status': 'waiting_student_is_whatsapp'}
    assert await post_callback(
        client,
        secret,
        7,
        telegram_user_id,
        'students:create:whatsapp:yes',
    ) == {'status': 'waiting_student_address_zip_code'}
    assert await post_text(
        client,
        secret,
        8,
        telegram_user_id,
        '74815705',
    ) == {'status': 'waiting_student_address_number'}
    assert await post_text(
        client,
        secret,
        9,
        telegram_user_id,
        '327',
    ) == {'status': 'waiting_student_address_complement'}
    assert await post_text(
        client,
        secret,
        10,
        telegram_user_id,
        'Casa 2',
    ) == {'status': 'waiting_student_cpf'}
    assert await post_text(
        client,
        secret,
        11,
        telegram_user_id,
        '12345678911',
    ) == {'status': 'waiting_student_instagram'}
    assert await post_text(
        client,
        secret,
        12,
        telegram_user_id,
        'NarutoUzumaki',
    ) == {'status': 'waiting_student_email'}
    assert await post_text(
        client,
        secret,
        13,
        telegram_user_id,
        'naruto@example.com',
    ) == {'status': 'waiting_student_birth_date'}
    assert await post_text(
        client,
        secret,
        14,
        telegram_user_id,
        '24/01/1994',
    ) == {'status': 'waiting_student_monthly_fee'}
    assert await post_text(
        client,
        secret,
        15,
        telegram_user_id,
        '250',
    ) == {'status': 'waiting_student_due_day'}
    assert await post_text(
        client,
        secret,
        16,
        telegram_user_id,
        '7',
    ) == {'status': 'waiting_student_confirmation'}

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
    assert await post_text(
        client,
        secret,
        102,
        telegram_user_id,
        'Lulu Nuna',
    ) == {'status': 'waiting_student_modality'}
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
    ) == {'status': 'waiting_student_responsible_relationship'}
    assert await post_callback(
        client,
        secret,
        106,
        telegram_user_id,
        'students:create:responsible:relationship:father',
    ) == {'status': 'waiting_student_responsible_name'}
    assert await post_text(
        client,
        secret,
        107,
        telegram_user_id,
        'Thiago Tancredi',
    ) == {'status': 'waiting_student_responsible_phone'}
    assert await post_text(
        client,
        secret,
        108,
        telegram_user_id,
        '62982551800',
    ) == {'status': 'waiting_student_responsible_is_whatsapp'}
    assert await post_callback(
        client,
        secret,
        109,
        telegram_user_id,
        'students:create:responsible:whatsapp:yes',
    ) == {'status': 'waiting_student_responsible_email'}
    assert await post_text(
        client,
        secret,
        110,
        telegram_user_id,
        'pai@example.com',
    ) == {'status': 'waiting_student_responsible_next_action'}
    assert await post_callback(
        client,
        secret,
        111,
        telegram_user_id,
        'students:create:responsible:continue',
    ) == {'status': 'waiting_student_address_zip_code'}
    assert await post_text(
        client,
        secret,
        112,
        telegram_user_id,
        '74815705',
    ) == {'status': 'waiting_student_address_number'}
    assert await post_text(
        client,
        secret,
        113,
        telegram_user_id,
        '327',
    ) == {'status': 'waiting_student_address_complement'}
    assert await post_text(
        client,
        secret,
        114,
        telegram_user_id,
        'Apartamento 902',
    ) == {'status': 'waiting_student_cpf'}
    assert await post_text(
        client,
        secret,
        115,
        telegram_user_id,
        '43256798712',
    ) == {'status': 'waiting_student_instagram'}
    assert await post_text(
        client,
        secret,
        116,
        telegram_user_id,
        'LunaNuninha',
    ) == {'status': 'waiting_student_email'}
    assert await post_text(
        client,
        secret,
        117,
        telegram_user_id,
        'luna@example.com',
    ) == {'status': 'waiting_student_birth_date'}
    assert await post_text(
        client,
        secret,
        118,
        telegram_user_id,
        '24/09/2020',
    ) == {'status': 'waiting_student_monthly_fee'}
    assert await post_text(
        client,
        secret,
        119,
        telegram_user_id,
        '350',
    ) == {'status': 'waiting_student_due_day'}
    assert await post_text(
        client,
        secret,
        120,
        telegram_user_id,
        '7',
    ) == {'status': 'waiting_student_confirmation'}

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
