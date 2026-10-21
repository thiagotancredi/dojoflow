import uuid
from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.services import billing as billing_module
from tests.helpers.auth import (
    auth_headers,
    create_modality,
    other_academy_headers,
)
from tests.helpers.scenario import add_modality, add_student


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
        'enrollments': [
            {
                'modality_id': modality_id,
                'monthly_fee': '150.00',
                'due_day': 10,
                **enrollment,
            }
        ],
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
    other_headers = await other_academy_headers(db_session)

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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('field', 'expected'),
    [
        ('status', HTTPStatus.UNPROCESSABLE_ENTITY),
        ('is_exempt', HTTPStatus.UNPROCESSABLE_ENTITY),
        ('monthly_fee', HTTPStatus.CONFLICT),
    ],
)
async def test_enrollment_patch_null_handling(
    client: AsyncClient,
    db_session: AsyncSession,
    field: str,
    expected: HTTPStatus,
) -> None:
    headers = await auth_headers(client)
    modality_id = await _enable_modality(client, db_session, headers, 'Jiu')
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(modality_id),
    )
    student_id = created.json()['id']
    detail = await client.get(
        f'/api/v1/students/{student_id}', headers=headers
    )
    enrollment_id = detail.json()['enrollments'][0]['id']

    response = await client.patch(
        f'/api/v1/students/{student_id}/enrollments/{enrollment_id}',
        headers=headers,
        json={field: None},
    )

    assert response.status_code == expected


@pytest.mark.asyncio
async def test_student_patch_null_name_is_rejected(
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

    response = await client.patch(
        f'/api/v1/students/{created.json()["id"]}',
        headers=headers,
        json={'name': None},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def _total_students(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.get('/api/v1/students', headers=headers)

    return response.json()['total']


@pytest.mark.asyncio
async def test_create_student_with_several_enrollments(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu = await _enable_modality(client, db_session, headers, 'Jiu')
    boxing = await _enable_modality(client, db_session, headers, 'Boxe')

    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json={
            'name': 'Ana Lima',
            'enrollments': [
                {'modality_id': jiu, 'monthly_fee': '150.00', 'due_day': 10},
                {'modality_id': boxing, 'is_exempt': True},
            ],
        },
    )

    assert created.status_code == HTTPStatus.CREATED, created.text
    detail = await client.get(
        f'/api/v1/students/{created.json()["id"]}', headers=headers
    )
    enrollments = {
        item['modality_id']: item for item in detail.json()['enrollments']
    }
    assert set(enrollments) == {jiu, boxing}
    assert enrollments[jiu]['monthly_fee'] == '150.00'
    assert enrollments[boxing]['is_exempt'] is True


@pytest.mark.asyncio
async def test_invalid_second_enrollment_creates_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu = await _enable_modality(client, db_session, headers, 'Jiu')
    not_offered = str((await create_modality(db_session, 'Boxe')).public_id)

    response = await client.post(
        '/api/v1/students',
        headers=headers,
        json={
            'name': 'Ana Lima',
            'enrollments': [
                {'modality_id': jiu, 'is_exempt': True},
                {'modality_id': not_offered, 'is_exempt': True},
            ],
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'MODALITY_NOT_ENABLED'
    assert await _total_students(client, headers) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('repeat', [True, False])
async def test_enrollments_must_be_non_empty_and_distinct(
    client: AsyncClient,
    db_session: AsyncSession,
    repeat: bool,
) -> None:
    headers = await auth_headers(client)
    jiu = await _enable_modality(client, db_session, headers, 'Jiu')
    enrollments = (
        [{'modality_id': jiu}, {'modality_id': jiu}] if repeat else []
    )

    response = await client.post(
        '/api/v1/students',
        headers=headers,
        json={'name': 'Ana Lima', 'enrollments': enrollments},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def _freeze_today(monkeypatch: pytest.MonkeyPatch, today: date) -> None:
    monkeypatch.setattr(billing_module, 'local_today', lambda: today)


async def _create(
    client: AsyncClient,
    db_session: AsyncSession,
    **enrollment: object,
) -> tuple[dict[str, str], str, object]:
    headers = await auth_headers(client)
    modality_id = await _enable_modality(client, db_session, headers, 'Jiu')
    response = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(modality_id, **enrollment),
    )
    return headers, modality_id, response


async def _charges(
    client: AsyncClient, headers: dict[str, str], student_id: str
) -> list[dict]:
    response = await client.get(
        f'/api/v1/students/{student_id}/billing', headers=headers
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()['charges']


async def _first_enrollment(
    client: AsyncClient, headers: dict[str, str], student_id: str
) -> str:
    detail = await client.get(
        f'/api/v1/students/{student_id}', headers=headers
    )
    return detail.json()['enrollments'][0]['id']


async def _billing_start(db_session: AsyncSession, enrollment_id: str) -> date:
    enrollment = await db_session.scalar(
        select(Enrollment).where(
            Enrollment.public_id == uuid.UUID(enrollment_id)
        )
    )
    await db_session.refresh(enrollment)
    return enrollment.billing_start_month


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'enrollment',
    [{'monthly_fee': None}, {'due_day': None}, {'monthly_fee': '0'}],
    ids=['no-fee', 'no-due-day', 'zero-fee'],
)
async def test_create_enrollment_without_fee_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    enrollment: dict,
) -> None:
    headers, _, response = await _create(client, db_session, **enrollment)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'ENROLLMENT_BILLING_INCOMPLETE'
    listing = await client.get('/api/v1/students', headers=headers)
    assert listing.json()['total'] == 0


@pytest.mark.asyncio
async def test_zero_fee_not_exempt_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, _, response = await _create(client, db_session, monthly_fee='0.00')

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()['code'] == 'ENROLLMENT_BILLING_INCOMPLETE'


@pytest.mark.asyncio
async def test_exempt_enrollment_needs_no_fee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, _, response = await _create(
        client, db_session, monthly_fee=None, due_day=None, is_exempt=True
    )

    assert response.status_code == HTTPStatus.CREATED, response.text


@pytest.mark.asyncio
async def test_create_enrollment_creates_enrollment_fee(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_today(monkeypatch, date(2026, 10, 20))
    headers, _, response = await _create(
        client, db_session, enrollment_fee='80'
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    student_id = response.json()['id']

    (fee,) = await _charges(client, headers, student_id)
    assert fee['kind'] == 'enrollment_fee'
    assert fee['amount'] == '80.00'
    assert fee['due_date'] == '2026-10-20'
    assert fee['reference_month'] == '2026-10-01'
    assert fee['status'] == 'upcoming'
    enrollment_id = await _first_enrollment(client, headers, student_id)
    assert await _billing_start(db_session, enrollment_id) == date(2026, 11, 1)

    _freeze_today(monkeypatch, date(2026, 10, 21))
    (fee,) = await _charges(client, headers, student_id)
    assert fee['status'] == 'overdue'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'enrollment', [{'enrollment_fee': '0'}, {}], ids=['zero', 'missing']
)
async def test_enrollment_fee_zero_is_waived(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    enrollment: dict,
) -> None:
    _freeze_today(monkeypatch, date(2026, 10, 20))
    headers, _, response = await _create(client, db_session, **enrollment)
    student_id = response.json()['id']

    (fee,) = await _charges(client, headers, student_id)

    assert fee['kind'] == 'enrollment_fee'
    assert fee['status'] == 'waived'


@pytest.mark.asyncio
async def test_add_enrollment_requires_fee_and_creates_fee(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_today(monkeypatch, date(2026, 10, 20))
    headers, _, response = await _create(client, db_session)
    student_id = response.json()['id']
    judo = await _enable_modality(client, db_session, headers, 'Judô')
    url = f'/api/v1/students/{student_id}/enrollments'

    incomplete = await client.post(
        url, headers=headers, json={'modality_id': judo, 'due_day': 5}
    )
    added = await client.post(
        url,
        headers=headers,
        json={
            'modality_id': judo,
            'monthly_fee': '90',
            'due_day': 5,
            'enrollment_fee': '50',
        },
    )

    assert incomplete.status_code == HTTPStatus.CONFLICT
    assert incomplete.json()['code'] == 'ENROLLMENT_BILLING_INCOMPLETE'
    assert added.status_code == HTTPStatus.NO_CONTENT, added.text
    fees = [
        (c['modality_name'], c['amount'], c['status'])
        for c in await _charges(client, headers, student_id)
    ]
    assert sorted(fees) == [
        ('Jiu', '0.00', 'waived'),
        ('Judô', '50.00', 'upcoming'),
    ]


@pytest.mark.asyncio
async def test_reactivation_restarts_billing_next_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_today(monkeypatch, date(2026, 10, 20))
    headers, _, response = await _create(client, db_session)
    student_id = response.json()['id']
    enrollment_id = await _first_enrollment(client, headers, student_id)
    url = f'/api/v1/students/{student_id}/enrollments/{enrollment_id}'
    await client.patch(url, headers=headers, json={'status': 'inactive'})

    _freeze_today(monkeypatch, date(2027, 1, 10))
    response = await client.patch(
        url, headers=headers, json={'status': 'active'}
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert await _billing_start(db_session, enrollment_id) == date(2027, 2, 1)
    # Nada de novembro a janeiro: só a taxa (isenta)
    assert [
        c['kind'] for c in await _charges(client, headers, student_id)
    ] == ['enrollment_fee']


@pytest.mark.asyncio
async def test_exempt_to_paid_starts_billing_next_month(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_today(monkeypatch, date(2026, 10, 20))
    headers, _, response = await _create(
        client, db_session, monthly_fee=None, due_day=None, is_exempt=True
    )
    student_id = response.json()['id']
    enrollment_id = await _first_enrollment(client, headers, student_id)
    assert await _billing_start(db_session, enrollment_id) is None
    url = f'/api/v1/students/{student_id}/enrollments/{enrollment_id}'

    _freeze_today(monkeypatch, date(2027, 1, 10))
    only_flag = await client.patch(
        url, headers=headers, json={'is_exempt': False}
    )
    completed = await client.patch(
        url,
        headers=headers,
        json={'is_exempt': False, 'monthly_fee': '100', 'due_day': 5},
    )

    assert only_flag.status_code == HTTPStatus.CONFLICT
    assert only_flag.json()['code'] == 'ENROLLMENT_BILLING_INCOMPLETE'
    assert completed.status_code == HTTPStatus.NO_CONTENT, completed.text
    assert await _billing_start(db_session, enrollment_id) == date(2027, 2, 1)


@pytest.mark.asyncio
async def test_old_incomplete_enrollment_can_be_inactivated_not_edited(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # Matrícula antiga sem valor (de antes das mensalidades)
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, enrollment_id = await add_student(db_session, taekwondo)
    url = f'/api/v1/students/{student_id}/enrollments/{enrollment_id}'

    edited = await client.patch(url, headers=headers, json={'due_day': 5})
    inactivated = await client.patch(
        url, headers=headers, json={'status': 'inactive'}
    )

    assert edited.status_code == HTTPStatus.CONFLICT
    assert edited.json()['code'] == 'ENROLLMENT_BILLING_INCOMPLETE'
    assert inactivated.status_code == HTTPStatus.NO_CONTENT
