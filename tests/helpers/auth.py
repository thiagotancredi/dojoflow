from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.modality import Modality
from tests.helpers.onboarding import register_web


async def auth_headers(
    client: AsyncClient,
    **overrides: Any,
) -> dict[str, str]:
    response, _ = await register_web(client, **overrides)
    token = response.json()['access_token']

    return {'Authorization': f'Bearer {token}'}


async def create_modality(
    db_session: AsyncSession,
    name: str,
    emoji: str = '🥋',
) -> Modality:
    modality = Modality(name=name, emoji=emoji, is_active=True)
    db_session.add(modality)
    await db_session.commit()
    await db_session.refresh(modality)

    return modality
