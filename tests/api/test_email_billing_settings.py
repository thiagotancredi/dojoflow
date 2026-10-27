from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.models.student import Student
from tests.helpers.auth import SEED, auth_headers, other_academy_headers
from tests.helpers.infinitepay import enable_infinitepay
from tests.helpers.scenario import add_modality, add_responsible, add_student

URL = '/api/v1/academy/email-billing'
EXCHANGE_URL = '/api/v1/auth/support/exchange'
ACADEMIES_URL = '/api/v1/admin/academies'
STUDENTS_IN_LIST = 2
SETTINGS_URL = '/api/v1/academy/billing-settings'
PIX_SETTINGS = {
    'pix_key': 'dojo@exemplo.com',
    'pix_key_type': 'email',
    'pix_city': 'Goiânia',
    'recipient_name': 'Dojo Pix',
}


async def _save_pix(client: AsyncClient, headers: dict[str, str]) -> None:
    response = await client.put(
        SETTINGS_URL, headers=headers, json=PIX_SETTINGS
    )
    assert response.status_code == HTTPStatus.OK, response.text


async def _set_email(
    session: AsyncSession, student_id: str, email: str
) -> None:
    await session.execute(
        update(Student)
        .where(Student.public_id == student_id)
        .values(email=email)
    )
    await session.commit()


@pytest.mark.asyncio
async def test_email_billing_starts_disabled(client: AsyncClient):
    headers = await auth_headers(client)

    before = await client.get(URL, headers=headers)
    await _save_pix(client, headers)
    after = await client.get(URL, headers=headers)

    assert before.status_code == HTTPStatus.OK, before.text
    assert before.json() == {
        'enabled': False,
        'can_enable': False,
        'students_without_email': 0,
    }
    assert after.json()['enabled'] is False
    assert after.json()['can_enable'] is True


@pytest.mark.asyncio
async def test_enable_without_pix_or_infinitepay_409(client: AsyncClient):
    headers = await auth_headers(client)

    response = await client.put(URL, headers=headers, json={'enabled': True})

    assert response.status_code == HTTPStatus.CONFLICT, response.text
    assert response.json()['code'] == 'BILLING_NOT_CONFIGURED'
    assert response.json()['detail'] == (
        'Configure a chave Pix ou ligue a InfinitePay antes de ligar a '
        'cobrança por e-mail.'
    )
    assert (await client.get(URL, headers=headers)).json()['enabled'] is False


@pytest.mark.asyncio
async def test_enable_with_pix_then_disable(client: AsyncClient):
    headers = await auth_headers(client)
    await _save_pix(client, headers)

    on = await client.put(URL, headers=headers, json={'enabled': True})
    read = await client.get(URL, headers=headers)
    off = await client.put(URL, headers=headers, json={'enabled': False})

    assert on.status_code == HTTPStatus.OK, on.text
    assert on.json()['enabled'] is True
    assert read.json()['enabled'] is True
    assert off.json()['enabled'] is False
    # Salvar o Pix de novo não mexe no interruptor
    await client.put(URL, headers=headers, json={'enabled': True})
    await _save_pix(client, headers)
    assert (await client.get(URL, headers=headers)).json()['enabled'] is True


@pytest.mark.asyncio
async def test_enable_with_infinitepay_only(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    await enable_infinitepay(db_session)

    response = await client.put(URL, headers=headers, json={'enabled': True})

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['enabled'] is True
    assert response.json()['can_enable'] is True


@pytest.mark.asyncio
async def test_students_without_email_count(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    judo = await add_modality(db_session, 'Judô')
    with_email, _ = await add_student(db_session, judo, 'Com Email')
    await _set_email(db_session, with_email, 'com@exemplo.com')
    minor, _ = await add_student(
        db_session, judo, 'Menor', birth_date='2015-03-10'
    )
    await add_responsible(db_session, minor, email='mae@exemplo.com')
    await add_student(db_session, judo, 'Sem Email')
    # Isento e inativo não entram na conta
    await add_student(db_session, judo, 'Isento', is_exempt=True)
    await add_student(db_session, judo, 'Parado', status='inactive')

    response = await client.get(URL, headers=headers)

    assert response.json()['students_without_email'] == 1


@pytest.mark.asyncio
async def test_preview_uses_academy_and_master(client: AsyncClient):
    headers = await auth_headers(client)

    response = await client.get(f'{URL}/preview', headers=headers)

    assert response.status_code == HTTPStatus.OK, response.text
    body = response.json()
    assert body['subject'] == f'Mensalidade disponível — {SEED.academy_name}'
    assert SEED.master_name in body['html']
    assert 'Lucas' in body['html']
    assert '/pagar/exemplo' in body['html']


@pytest.mark.asyncio
async def test_preview_in_support_mode_signs_as_academy_master(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
):
    await other_academy_headers(db_session)
    academy = await db_session.scalar(
        select(Academy).where(Academy.name == 'Outra Academia')
    )
    entry = await client.post(
        f'{ACADEMIES_URL}/{academy.public_id}/support-entry',
        headers=admin_headers,
    )
    exchange = await client.post(
        EXCHANGE_URL, json={'code': entry.json()['code']}
    )
    client.cookies.clear()
    headers = {
        'Authorization': f'Bearer {exchange.json()["access_token"]}'
    }

    response = await client.get(f'{URL}/preview', headers=headers)

    assert response.status_code == HTTPStatus.OK, response.text
    body = response.json()
    assert body['subject'] == 'Mensalidade disponível — Outra Academia'
    assert 'Outro Mestre' in body['html']
    assert SEED.master_name not in body['html']


@pytest.mark.asyncio
async def test_students_list_missing_email_filter(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await auth_headers(client)
    judo = await add_modality(db_session, 'Judô')
    with_email, _ = await add_student(db_session, judo, 'Com Email')
    await _set_email(db_session, with_email, 'com@exemplo.com')
    await add_student(db_session, judo, 'Sem Email')

    everyone = await client.get('/api/v1/students', headers=headers)
    missing = await client.get(
        '/api/v1/students?missing_email=true', headers=headers
    )

    assert everyone.json()['total'] == STUDENTS_IN_LIST
    assert missing.status_code == HTTPStatus.OK, missing.text
    assert missing.json()['total'] == 1
    assert [i['name'] for i in missing.json()['items']] == ['Sem Email']


@pytest.mark.asyncio
async def test_other_academy_cannot_see_or_change(
    client: AsyncClient, db_session: AsyncSession
):
    mine = await auth_headers(client)
    theirs = await other_academy_headers(db_session)
    await _save_pix(client, mine)
    await client.put(URL, headers=mine, json={'enabled': True})
    judo = await add_modality(db_session, 'Judô')
    await add_student(db_session, judo, 'Sem Email')

    other = await client.get(URL, headers=theirs)
    refused = await client.put(URL, headers=theirs, json={'enabled': True})
    other_preview = await client.get(f'{URL}/preview', headers=theirs)

    assert other.json() == {
        'enabled': False,
        'can_enable': False,
        'students_without_email': 0,
    }
    assert refused.status_code == HTTPStatus.CONFLICT
    assert 'Outro Mestre' in other_preview.json()['html']
    assert (await client.get(URL, headers=mine)).json()[
        'students_without_email'
    ] == 1
