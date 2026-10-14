from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import unit_of_work
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from tests.helpers.onboarding import register_web


@pytest.mark.asyncio
async def test_revoke_all_for_master(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response, _ = await register_web(client)
    master_id = response.json()['master']['master_id']
    repository = RefreshSessionRepository(db_session=db_session)
    expires_at = datetime.now(UTC) + timedelta(days=1)

    async with unit_of_work(db_session):
        for token_hash in ('a' * 64, 'b' * 64):
            await repository.create({
                'master_id': master_id,
                'token_hash': token_hash,
                'expires_at': expires_at,
            })

    async with unit_of_work(db_session):
        await repository.revoke_all_for_master(
            master_id=master_id,
            revoked_at=datetime.now(UTC),
        )

    record = await repository.get_by_token_hash('a' * 64)

    assert record is not None
    assert record['revoked_at'] is not None
