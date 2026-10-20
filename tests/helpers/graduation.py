from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import create_modality


async def enable_modality(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict[str, str],
    name: str,
) -> str:
    modality = await create_modality(db_session, name)
    modality_id = str(modality.public_id)
    await toggle_modality(client, headers, modality_id)

    return modality_id


async def toggle_modality(
    client: AsyncClient,
    headers: dict[str, str],
    modality_id: str,
) -> None:
    response = await client.put(
        f'/api/v1/academy/modalities/{modality_id}/toggle',
        headers=headers,
    )
    assert response.status_code == 200, response.text  # noqa: PLR2004


async def create_belt(
    client: AsyncClient,
    headers: dict[str, str],
    modality_id: str,
    name: str,
    **fields: Any,
) -> dict[str, Any]:
    payload = {'name': name, 'primary_color': '#f8fafc', **fields}
    response = await client.post(
        f'/api/v1/academy/modalities/{modality_id}/belts',
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201, response.text  # noqa: PLR2004

    return response.json()


async def create_student(
    client: AsyncClient,
    headers: dict[str, str],
    modality_id: str,
    name: str = 'Ana Lima',
    status: str = 'active',
) -> tuple[str, str]:
    response = await client.post(
        '/api/v1/students',
        headers=headers,
        json={
            'name': name,
            'enrollment': {'modality_id': modality_id, 'status': status},
        },
    )
    assert response.status_code == 201, response.text  # noqa: PLR2004
    student_id = response.json()['id']

    detail = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )
    enrollment = next(
        item
        for item in detail.json()['enrollments']
        if item['modality_id'] == modality_id
    )

    return student_id, enrollment['id']
