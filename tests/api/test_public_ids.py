import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.public_ids import resolve_public_id
from dojoflow.models.modality import Modality
from dojoflow.shared.exceptions import NotFoundError
from tests.helpers.auth import create_modality


@pytest.mark.asyncio
async def test_resolves_existing_public_id(db_session: AsyncSession) -> None:
    modality = await create_modality(db_session, 'Judô')

    resolved = await resolve_public_id(
        db_session,
        Modality,
        modality.public_id,
        code='MODALITY_NOT_FOUND',
    )

    assert resolved == modality.id


@pytest.mark.asyncio
async def test_unknown_public_id_raises_with_code(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(NotFoundError) as error:
        await resolve_public_id(
            db_session,
            Modality,
            uuid.uuid4(),
            code='MODALITY_NOT_FOUND',
        )

    assert error.value.code == 'MODALITY_NOT_FOUND'
