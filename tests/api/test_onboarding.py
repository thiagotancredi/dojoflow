from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.models.master import Master
from tests.helpers.onboarding import register_onboarding


@pytest.mark.asyncio
async def test_register_onboarding_should_create_academy_and_master(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response, payload = await register_onboarding(client)

    assert response.status_code == HTTPStatus.CREATED

    body = response.json()

    assert body['academy_id'] is not None
    assert body['master_id'] is not None

    academy_result = await db_session.execute(
        select(Academy).where(Academy.id == body['academy_id'])
    )
    academy = academy_result.scalar_one()

    master_result = await db_session.execute(
        select(Master).where(Master.id == body['master_id'])
    )
    master = master_result.scalar_one()

    assert academy.name == payload['academy_name']

    assert master.name == payload['master_name']
    assert master.telegram_user_id == payload['telegram_user_id']
    assert master.phone == payload['phone']
    assert master.academy_id == academy.id


@pytest.mark.asyncio
async def test_register_onboarding_conflict_when_telegram_exists(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    first_response, payload = await register_onboarding(client)

    second_response, _ = await register_onboarding(
        client,
        telegram_user_id=payload['telegram_user_id'],
    )

    assert first_response.status_code == HTTPStatus.CREATED
    assert second_response.status_code == HTTPStatus.CONFLICT
    assert second_response.json() == {
        'detail': 'This Telegram user is already registered as a master.'
    }

    academy_count = await db_session.scalar(
        select(func.count()).select_from(Academy)
    )
    master_count = await db_session.scalar(
        select(func.count()).select_from(Master)
    )

    assert academy_count == 1
    assert master_count == 1


@pytest.mark.asyncio
async def test_register_onboarding_invalid_payload_should_return_422(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response, _ = await register_onboarding(
        client,
        telegram_user_id=0,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    academy_count = await db_session.scalar(
        select(func.count()).select_from(Academy)
    )
    master_count = await db_session.scalar(
        select(func.count()).select_from(Master)
    )

    assert academy_count == 0
    assert master_count == 0
