import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality


@pytest.mark.asyncio
async def test_catalog_and_toggle_use_public_ids(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality = await create_modality(db_session, 'Jiu-Jitsu')
    public_id = str(modality.public_id)

    catalog = await client.get('/api/v1/modalities/catalog', headers=headers)

    assert catalog.status_code == HTTPStatus.OK
    assert catalog.json() == [
        {'id': public_id, 'name': 'Jiu-Jitsu', 'emoji': '🥋'}
    ]

    toggle = await client.put(
        f'/api/v1/academy/modalities/{public_id}/toggle',
        headers=headers,
    )

    assert toggle.status_code == HTTPStatus.OK
    assert toggle.json() == {'is_selected': True}

    options = await client.get('/api/v1/academy/modalities', headers=headers)

    assert options.json() == [
        {
            'id': public_id,
            'name': 'Jiu-Jitsu',
            'emoji': '🥋',
            'is_selected': True,
            'has_belts': False,
        }
    ]


@pytest.mark.asyncio
async def test_toggle_unknown_modality_is_not_found(
    client: AsyncClient,
) -> None:
    headers = await auth_headers(client)

    response = await client.put(
        f'/api/v1/academy/modalities/{uuid.uuid4()}/toggle',
        headers=headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'MODALITY_NOT_FOUND'


@pytest.mark.asyncio
async def test_toggle_with_integer_id_is_rejected(
    client: AsyncClient,
) -> None:
    headers = await auth_headers(client)

    response = await client.put(
        '/api/v1/academy/modalities/1/toggle',
        headers=headers,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
