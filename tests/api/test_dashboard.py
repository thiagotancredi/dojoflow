from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import (
    auth_headers,
    create_modality,
    other_academy_headers,
)
from tests.helpers.scenario import (
    add_student,
)

ACTIVE_STUDENTS = 3


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
                'enrollments': [
                    {'modality_id': str(modality_id), **enrollment}
                ],
            },
        )
        assert response.status_code == HTTPStatus.CREATED

    await student('Ana', jiu.public_id, monthly_fee='150', due_day=10)
    # Matrícula antiga, sem valor (pendência de cadastro)
    await add_student(db_session, str(jiu.public_id), name='Bruno')
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
    # Matrícula antiga, sem valor (pendência de cadastro)
    await add_student(db_session, str(jiu.public_id), name='Ana')

    headers_b = await other_academy_headers(db_session)

    response_b = await client.get(
        '/api/v1/dashboard/summary', headers=headers_b
    )
    response_a = await client.get(
        '/api/v1/dashboard/summary', headers=headers_a
    )

    body_b = response_b.json()
    # Os 12 meses existem sempre (com zero); o resto vem vazio
    assert [m['count'] for m in body_b.pop('new_students_by_month')] == [
        0
    ] * 12
    assert body_b == {
        'active_students': 0,
        'students_by_modality': [],
        'age_groups': {
            'all': [
                {'group': group, 'count': 0}
                for group in ('kids', 'juvenile', 'adult', 'master', 'unknown')
            ],
            'by_modality': [],
        },
        'birthdays': [],
        'by_belt': [],
        'by_sex': [],
    }
    body_a = response_a.json()
    assert body_a['active_students'] == 1
