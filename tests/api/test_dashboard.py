from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality

ACTIVE_STUDENTS = 3
TOTAL_ENROLLMENTS = 4


@pytest.mark.asyncio
async def test_dashboard_summary(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu = await create_modality(db_session, 'Jiu')
    judo = await create_modality(db_session, 'Judô')

    for modality in (jiu, judo):
        await client.put(
            f'/api/v1/academy/modalities/{modality.public_id}/toggle',
            headers=headers,
        )

    async def student(name: str, modality_id: object, **enrollment: object):
        response = await client.post(
            '/api/v1/students',
            headers=headers,
            json={
                'name': name,
                'enrollment': {'modality_id': str(modality_id), **enrollment},
            },
        )
        assert response.status_code == HTTPStatus.CREATED

    await student('Ana', jiu.public_id, monthly_fee='150', due_day=10)
    await student('Bruno', jiu.public_id)
    await student('Carla', judo.public_id, is_exempt=True)
    await student('Davi', judo.public_id, status='inactive')

    response = await client.get('/api/v1/dashboard/summary', headers=headers)

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['active_students'] == ACTIVE_STUDENTS
    assert [
        (item['modality_name'], item['count'])
        for item in body['students_by_modality']
    ] == [('Jiu', 2), ('Judô', 1)]
    assert [item['student_name'] for item in body['registration_pending']] == [
        'Bruno'
    ]
    assert len(body['recent_enrollments']) == TOTAL_ENROLLMENTS
    assert body['recent_enrollments'][0]['student_name'] == 'Davi'


@pytest.mark.asyncio
async def test_dashboard_isolated_per_academy(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers_a = await auth_headers(client)
    jiu = await create_modality(db_session, 'Jiu')
    await client.put(
        f'/api/v1/academy/modalities/{jiu.public_id}/toggle',
        headers=headers_a,
    )
    created = await client.post(
        '/api/v1/students',
        headers=headers_a,
        json={
            'name': 'Ana',
            'enrollment': {'modality_id': str(jiu.public_id)},
        },
    )
    assert created.status_code == HTTPStatus.CREATED

    headers_b = await auth_headers(
        client,
        email='outro@dojoflow.test',
        academy_name='Outra Academia',
    )

    response_b = await client.get(
        '/api/v1/dashboard/summary', headers=headers_b
    )
    response_a = await client.get(
        '/api/v1/dashboard/summary', headers=headers_a
    )

    assert response_b.json() == {
        'active_students': 0,
        'students_by_modality': [],
        'recent_enrollments': [],
        'registration_pending': [],
    }
    body_a = response_a.json()
    assert body_a['active_students'] == 1
    assert len(body_a['recent_enrollments']) == 1
    assert [i['student_name'] for i in body_a['registration_pending']] == [
        'Ana'
    ]
