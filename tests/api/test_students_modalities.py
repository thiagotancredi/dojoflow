from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.modality import Modality
from dojoflow.shared.enums import StudentSex
from tests.helpers.onboarding import register_web


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    response, _ = await register_web(client)
    token = response.json()['access_token']

    return {'Authorization': f'Bearer {token}'}


@pytest.mark.asyncio
async def test_modalities_catalog_and_toggle(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client)

    modality = Modality(
        name='Jiu-Jitsu',
        emoji='🥋',
        is_active=True,
    )
    db_session.add(modality)
    await db_session.commit()
    await db_session.refresh(modality)

    catalog_response = await client.get(
        '/api/v1/modalities/catalog',
        headers=headers,
    )

    assert catalog_response.status_code == HTTPStatus.OK
    assert any(
        item['id'] == modality.id for item in catalog_response.json()
    )

    toggle_response = await client.put(
        f'/api/v1/academy/modalities/{modality.id}/toggle',
        headers=headers,
    )

    assert toggle_response.status_code == HTTPStatus.OK
    assert toggle_response.json() == {'is_selected': True}

    academy_response = await client.get(
        '/api/v1/academy/modalities',
        headers=headers,
    )

    assert academy_response.status_code == HTTPStatus.OK
    selected = [
        item
        for item in academy_response.json()
        if item['id'] == modality.id
    ]
    assert selected[0]['is_selected'] is True


@pytest.mark.asyncio
async def test_students_rest_crud_flow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _auth_headers(client)

    modality = Modality(
        name='Muay Thai',
        emoji='🥊',
        is_active=True,
    )
    db_session.add(modality)
    await db_session.commit()
    await db_session.refresh(modality)

    await client.put(
        f'/api/v1/academy/modalities/{modality.id}/toggle',
        headers=headers,
    )

    create_response = await client.post(
        '/api/v1/students',
        headers=headers,
        json={
            'name': 'Aluno Teste',
            'phone': '62999998888',
            'phone_is_whatsapp': True,
            'sex': StudentSex.MALE.value,
            'enrollment': {
                'modality_id': modality.id,
                'monthly_fee': '200.00',
                'due_day': 10,
                'is_exempt': False,
            },
        },
    )

    assert create_response.status_code == HTTPStatus.CREATED
    student = create_response.json()
    assert student['name'] == 'Aluno Teste'

    list_response = await client.get(
        '/api/v1/students',
        headers=headers,
    )

    assert list_response.status_code == HTTPStatus.OK
    assert len(list_response.json()) == 1

    details_response = await client.get(
        f'/api/v1/students/{student["id"]}',
        headers=headers,
    )

    assert details_response.status_code == HTTPStatus.OK
    assert details_response.json()['student']['id'] == student['id']

    patch_response = await client.patch(
        f'/api/v1/students/{student["id"]}',
        headers=headers,
        json={'name': 'Aluno Atualizado'},
    )

    assert patch_response.status_code == HTTPStatus.NO_CONTENT

    details_after_patch = await client.get(
        f'/api/v1/students/{student["id"]}',
        headers=headers,
    )

    assert details_after_patch.json()['student']['name'] == 'Aluno Atualizado'


@pytest.mark.asyncio
async def test_students_require_auth(
    client: AsyncClient,
) -> None:
    response = await client.get('/api/v1/students')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
