import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.models.academy import Academy
from dojoflow.models.master import Master
from dojoflow.models.one_time_token import OneTimeToken
from dojoflow.repositories.academy import AcademyRepository
from dojoflow.repositories.master import MasterRepository
from dojoflow.repositories.one_time_token import OneTimeTokenRepository
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from dojoflow.services.academy import AcademyService
from dojoflow.services.auth import AuthService
from dojoflow.services.master import MasterService
from dojoflow.services.onboarding import OnboardingService
from tests.helpers.onboarding import register_onboarding, register_web

EXPECTED_ACADEMY_COUNT = 2
EXPECTED_MASTER_COUNT = 2


@pytest.mark.asyncio
async def test_register_web_should_create_academy_and_master_without_telegram(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response, payload = await register_web(client)

    assert response.status_code == HTTPStatus.CREATED

    body = response.json()

    assert body['access_token']
    assert response.cookies['dojoflow_refresh']
    assert body['master']['email'] == payload['email']
    assert body['master']['telegram_linked'] is False
    assert body['master']['academy']['name'] == payload['academy_name']
    assert set(body['master']) == {
        'id',
        'name',
        'email',
        'telegram_linked',
        'academy',
    }
    assert set(body['master']['academy']) == {'id', 'name', 'status'}
    uuid.UUID(body['master']['id'])
    uuid.UUID(body['master']['academy']['id'])

    master = (
        await db_session.execute(
            select(Master).where(Master.email == payload['email'])
        )
    ).scalar_one()

    assert master.telegram_user_id is None
    assert master.password_hash is not None
    assert master.password_hash != payload['password']


@pytest.mark.asyncio
async def test_register_web_conflict_when_email_exists(
    client: AsyncClient,
) -> None:
    first_response, payload = await register_web(client)
    second_response, _ = await register_web(
        client,
        email=payload['email'],
        academy_name='Outra Academia',
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert second_response.status_code == HTTPStatus.CONFLICT
    assert second_response.json() == {
        'detail': 'This email is already registered as a master.',
        'code': 'EMAIL_ALREADY_REGISTERED',
    }


@pytest.mark.asyncio
async def test_login_and_me(
    client: AsyncClient,
) -> None:
    register_response, payload = await register_web(client)
    assert register_response.status_code == HTTPStatus.CREATED

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': payload['email'],
            'password': payload['password'],
        },
    )

    assert login_response.status_code == HTTPStatus.OK
    tokens = login_response.json()

    me_response = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {tokens["access_token"]}'},
    )

    assert me_response.status_code == HTTPStatus.OK
    me = me_response.json()

    assert me['email'] == payload['email']
    assert me['id'] == tokens['master']['id']
    assert 'master_id' not in me
    assert 'academy_id' not in me


@pytest.mark.asyncio
async def test_login_invalid_password(
    client: AsyncClient,
) -> None:
    _, payload = await register_web(client)

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': payload['email'],
            'password': 'senha-errada',
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'INVALID_CREDENTIALS'


@pytest.mark.asyncio
async def test_login_unknown_email_has_same_error_code(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/login',
        json={'email': 'ninguem@dojoflow.test', 'password': 'senha-segura'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'INVALID_CREDENTIALS'


@pytest.mark.asyncio
async def test_telegram_link_token_and_webhook_link(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.TELEGRAM_WEBHOOK_SECRET = 'webhook-secret'

    async def fake_send_message(
        self: object,
        **kwargs: object,
    ) -> dict[str, str]:
        return {'ok': 'true'}

    monkeypatch.setattr(TelegramService, 'send_message', fake_send_message)

    register_response, _ = await register_web(client)
    access_token = register_response.json()['access_token']
    master_public_id = register_response.json()['master']['id']

    link_response = await client.post(
        '/api/v1/auth/telegram/link-token',
        headers={'Authorization': f'Bearer {access_token}'},
    )

    assert link_response.status_code == HTTPStatus.OK
    link_body = link_response.json()
    assert link_body['token']
    assert link_body['deep_link'] is not None

    telegram_user_id = 555666777

    webhook_response = await client.post(
        '/api/v1/telegram/webhook',
        headers={'X-Telegram-Bot-Api-Secret-Token': 'webhook-secret'},
        json={
            'update_id': 1,
            'message': {
                'message_id': 1,
                'date': 1,
                'text': f'/start link_{link_body["token"]}',
                'chat': {'id': telegram_user_id, 'type': 'private'},
                'from': {
                    'id': telegram_user_id,
                    'is_bot': False,
                    'first_name': 'Mestre',
                },
            },
        },
    )

    assert webhook_response.status_code == HTTPStatus.OK
    assert webhook_response.json() == {'status': 'telegram_linked'}

    master = (
        await db_session.execute(
            select(Master).where(
                Master.public_id == uuid.UUID(master_public_id)
            )
        )
    ).scalar_one()

    assert master.telegram_user_id == telegram_user_id

    used_token = (
        await db_session.execute(
            select(OneTimeToken).where(
                OneTimeToken.token == link_body['token']
            )
        )
    ).scalar_one()

    assert used_token.used_at is not None


@pytest.mark.asyncio
async def test_set_credentials_with_setup_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    onboarding_response, _ = await register_onboarding(client)
    master_id = onboarding_response.json()['master_id']
    master_public_id = (
        await db_session.execute(
            select(Master.public_id).where(Master.id == master_id)
        )
    ).scalar_one()

    master_repository = MasterRepository(db_session=db_session)
    academy_repository = AcademyRepository(db_session=db_session)
    master_service = MasterService(
        master_repository=master_repository,
        db_session=db_session,
    )
    academy_service = AcademyService(
        academy_repository=academy_repository,
        db_session=db_session,
    )
    onboarding_service = OnboardingService(
        academy_service=academy_service,
        master_service=master_service,
        db_session=db_session,
    )
    auth_service = AuthService(
        onboarding_service=onboarding_service,
        master_service=master_service,
        one_time_token_repository=OneTimeTokenRepository(
            db_session=db_session
        ),
        refresh_session_repository=RefreshSessionRepository(
            db_session=db_session
        ),
        db_session=db_session,
    )

    setup = await auth_service.create_telegram_setup_token_for_master(
        master_id
    )

    response = await client.post(
        '/api/v1/auth/set-credentials',
        json={
            'email': 'telegram.mestre@dojoflow.test',
            'password': 'senha-segura',
            'setup_token': setup.token,
        },
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['master']['email'] == 'telegram.mestre@dojoflow.test'
    assert body['master']['telegram_linked'] is True
    assert body['master']['id'] == str(master_public_id)

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'telegram.mestre@dojoflow.test',
            'password': 'senha-segura',
        },
    )

    assert login_response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_register_onboarding_http_requires_internal_key_when_disabled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, 'INTERNAL_API_KEY', '')

    response = await client.post(
        '/api/v1/onboarding',
        json={
            'academy_name': 'Academia',
            'master_name': 'Mestre',
            'telegram_user_id': 12345,
        },
    )

    assert response.status_code == HTTPStatus.GONE


@pytest.mark.asyncio
async def test_telegram_and_web_registration_both_work(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    telegram_response, _ = await register_onboarding(client)
    web_response, _ = await register_web(
        client,
        email='outro@dojoflow.test',
        academy_name='Academia Site',
    )

    assert telegram_response.status_code == HTTPStatus.CREATED
    assert web_response.status_code == HTTPStatus.CREATED

    academy_count = await db_session.scalar(
        select(func.count()).select_from(Academy)
    )
    master_count = await db_session.scalar(
        select(func.count()).select_from(Master)
    )

    assert academy_count == EXPECTED_ACADEMY_COUNT
    assert master_count == EXPECTED_MASTER_COUNT
