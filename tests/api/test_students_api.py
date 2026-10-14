import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality


async def _enable_modality(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict[str, str],
    name: str,
) -> str:
    modality = await create_modality(db_session, name)
    public_id = str(modality.public_id)
    await client.put(
        f'/api/v1/academy/modalities/{public_id}/toggle',
        headers=headers,
    )

    return public_id


def _create_payload(modality_id: str, **enrollment: object) -> dict:
    return {
        'name': 'Ana Lima',
        'phone': '62999990001',
        'phone_is_whatsapp': True,
        'sex': 'female',
        'enrollment': {
            'modality_id': modality_id,
            'monthly_fee': '150.00',
            'due_day': 10,
            **enrollment,
        },
        'address': {
            'zip_code': '74000000',
            'street': 'Rua A',
            'city': 'Goiânia',
            'state': 'GO',
            'number': '10',
        },
        'responsibles': [
            {
                'name': 'Maria Lima',
                'phone': '62999990002',
                'phone_is_whatsapp': True,
                'relationship': 'mother',
            }
        ],
    }


@pytest.mark.asyncio
async def test_create_and_read_student_detail_with_public_ids(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu_jitsu = await _enable_modality(client, db_session, headers, 'Jiu')

    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(jiu_jitsu),
    )

    assert created.status_code == HTTPStatus.CREATED
    student_id = created.json()['id']
    uuid.UUID(student_id)

    detail = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )

    assert detail.status_code == HTTPStatus.OK
    body = detail.json()
    assert body['student']['id'] == student_id
    assert body['address']['city'] == 'Goiânia'
    assert body['responsibles'][0]['relationship'] == 'mother'
    uuid.UUID(body['responsibles'][0]['id'])
    enrollment = body['enrollments'][0]
    assert enrollment['modality_id'] == jiu_jitsu
    assert enrollment['modality_name'] == 'Jiu'
    assert enrollment['monthly_fee'] == '150.00'
    uuid.UUID(enrollment['id'])


@pytest.mark.asyncio
async def test_due_day_above_28_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality_id = await _enable_modality(client, db_session, headers, 'Judô')

    response = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(modality_id, due_day=31),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_add_and_update_specific_enrollment(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu_jitsu = await _enable_modality(client, db_session, headers, 'Jiu')
    judo = await _enable_modality(client, db_session, headers, 'Judô')
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(jiu_jitsu),
    )
    student_id = created.json()['id']

    added = await client.post(
        f'/api/v1/students/{student_id}/enrollments',
        headers=headers,
        json={'modality_id': judo, 'is_exempt': True},
    )
    duplicate = await client.post(
        f'/api/v1/students/{student_id}/enrollments',
        headers=headers,
        json={'modality_id': judo},
    )

    assert added.status_code == HTTPStatus.NO_CONTENT
    assert duplicate.status_code == HTTPStatus.CONFLICT
    assert duplicate.json()['code'] == 'ENROLLMENT_ALREADY_EXISTS'

    detail = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )
    judo_enrollment = next(
        item
        for item in detail.json()['enrollments']
        if item['modality_id'] == judo
    )

    updated = await client.patch(
        f'/api/v1/students/{student_id}/enrollments/{judo_enrollment["id"]}',
        headers=headers,
        json={'status': 'inactive'},
    )

    assert updated.status_code == HTTPStatus.NO_CONTENT

    after = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )
    statuses = {
        item['modality_id']: item['status']
        for item in after.json()['enrollments']
    }
    assert statuses == {jiu_jitsu: 'active', judo: 'inactive'}


@pytest.mark.asyncio
async def test_student_from_other_academy_is_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await auth_headers(client)
    modality_id = await _enable_modality(
        client, db_session, owner_headers, 'Jiu'
    )
    created = await client.post(
        '/api/v1/students',
        headers=owner_headers,
        json=_create_payload(modality_id),
    )
    other_headers = await auth_headers(
        client,
        email='outro@dojoflow.test',
        academy_name='Outra Academia',
    )

    response = await client.get(
        f'/api/v1/students/{created.json()["id"]}',
        headers=other_headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'STUDENT_NOT_FOUND'


@pytest.mark.asyncio
async def test_update_basic_data(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality_id = await _enable_modality(client, db_session, headers, 'Jiu')
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(modality_id),
    )
    student_id = created.json()['id']

    patched = await client.patch(
        f'/api/v1/students/{student_id}',
        headers=headers,
        json={'name': 'Ana Atualizada'},
    )
    detail = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )

    assert patched.status_code == HTTPStatus.NO_CONTENT
    assert detail.json()['student']['name'] == 'Ana Atualizada'


@pytest.mark.asyncio
async def test_students_require_auth(client: AsyncClient) -> None:
    response = await client.get(f'/api/v1/students/{uuid.uuid4()}')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
