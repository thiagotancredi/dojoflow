import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality


@pytest.mark.asyncio
async def test_remove_responsible_link(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality = await create_modality(db_session, 'Jiu')
    await client.put(
        f'/api/v1/academy/modalities/{modality.public_id}/toggle',
        headers=headers,
    )
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json={
            'name': 'Davi Rocha',
            'enrollments': [{'modality_id': str(modality.public_id)}],
            'responsibles': [
                {
                    'name': 'Paula Rocha',
                    'phone': '62999990003',
                    'relationship': 'mother',
                }
            ],
        },
    )
    student_id = created.json()['id']
    detail = await client.get(
        f'/api/v1/students/{student_id}', headers=headers
    )
    link_id = detail.json()['responsibles'][0]['id']

    removed = await client.delete(
        f'/api/v1/students/{student_id}/responsibles/{link_id}',
        headers=headers,
    )
    missing = await client.delete(
        f'/api/v1/students/{student_id}/responsibles/{uuid.uuid4()}',
        headers=headers,
    )
    after = await client.get(f'/api/v1/students/{student_id}', headers=headers)

    assert removed.status_code == HTTPStatus.NO_CONTENT
    assert missing.status_code == HTTPStatus.NOT_FOUND
    assert missing.json()['code'] == 'RESPONSIBLE_LINK_NOT_FOUND'
    assert after.json()['responsibles'] == []
