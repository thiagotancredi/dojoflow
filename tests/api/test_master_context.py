from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.shared.enums import AcademyStatus
from tests.helpers.onboarding import register_onboarding


@pytest.mark.asyncio
async def test_get_master_context_should_return_context(
    client: AsyncClient,
) -> None:
    onboarding_response, payload = await register_onboarding(client)
    onboarding_body = onboarding_response.json()

    response = await client.get(
        f'/api/v1/masters/context/{payload["telegram_user_id"]}'
    )

    assert response.status_code == HTTPStatus.OK

    body = response.json()

    assert body == {
        'master_id': onboarding_body['master_id'],
        'master_name': payload['master_name'],
        'telegram_user_id': payload['telegram_user_id'],
        'academy_id': onboarding_body['academy_id'],
        'academy_name': payload['academy_name'],
        'academy_status': 'active',
    }


@pytest.mark.asyncio
async def test_get_master_context_should_return_blocked_academy_status(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    onboarding_response, payload = await register_onboarding(client)
    onboarding_body = onboarding_response.json()

    academy_result = await db_session.execute(
        select(Academy).where(
            Academy.id == onboarding_body['academy_id'],
        )
    )
    academy = academy_result.scalar_one()
    academy.status = AcademyStatus.BLOCKED

    await db_session.commit()

    response = await client.get(
        f'/api/v1/masters/context/{payload["telegram_user_id"]}'
    )

    assert response.status_code == HTTPStatus.OK

    body = response.json()

    assert body['academy_status'] == 'blocked'


@pytest.mark.asyncio
async def test_get_master_context_should_return_404_when_not_found(
    client: AsyncClient,
) -> None:
    response = await client.get('/api/v1/masters/context/999999999')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        'detail': 'Master context not found.',
    }
