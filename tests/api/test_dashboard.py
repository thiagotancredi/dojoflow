from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.services import billing as billing_module
from tests.helpers.auth import (
    auth_headers,
    create_modality,
    other_academy_headers,
)
from tests.helpers.scenario import add_modality, add_student

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
    # Matrícula antiga, sem valor (pendência de cadastro)
    await add_student(db_session, str(jiu.public_id), name='Ana')

    headers_b = await other_academy_headers(db_session)

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
        'overdue': [],
        'due_soon': [],
        'overdue_students': 0,
        'due_soon_students': 0,
    }
    body_a = response_a.json()
    assert body_a['active_students'] == 1
    assert len(body_a['recent_enrollments']) == 1
    assert [i['student_name'] for i in body_a['registration_pending']] == [
        'Ana'
    ]


@pytest.mark.asyncio
async def test_dashboard_overdue_and_due_soon(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = await auth_headers(client)
    jiu = await add_modality(db_session, 'Jiu')
    # Ana: janeiro e fevereiro atrasados (dia 15); Bruno: vence dia 25
    await add_student(
        db_session,
        jiu,
        name='Ana Lima',
        monthly_fee='100',
        due_day=15,
        billing_start_month='2027-01-01',
    )
    await add_student(
        db_session,
        jiu,
        name='Bruno Dias',
        monthly_fee='80',
        due_day=25,
        billing_start_month='2027-02-01',
    )
    monkeypatch.setattr(
        billing_module, 'local_today', lambda: date(2027, 2, 20)
    )

    body = (
        await client.get('/api/v1/dashboard/summary', headers=headers)
    ).json()

    assert [
        (i['name'], i['modality'], i['amount'], i['days_late'])
        for i in body['overdue']
    ] == [('Ana Lima', 'Jiu', '200.00', 36)]
    assert [
        (i['name'], i['modality'], i['amount'], i['due_date'])
        for i in body['due_soon']
    ] == [('Bruno Dias', 'Jiu', '80.00', '2027-02-25')]
    # Totais para os números do topo (as listas param em 5)
    assert body['overdue_students'] == 1
    assert body['due_soon_students'] == 1
