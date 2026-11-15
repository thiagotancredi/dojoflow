"""Estatísticas, "Cadastro incompleto": quem não tem para quem mandar a
cobrança, sem data de nascimento e menor sem responsável. Tocar no número
abre Alunos filtrado."""

from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.student import Student
from dojoflow.services import dashboard as dashboard_module
from dojoflow.services import incomplete_records as incomplete_module
from dojoflow.services.incomplete_records import incomplete_student_ids
from tests.helpers.auth import SEED, auth_headers
from tests.helpers.scenario import (
    add_modality,
    add_responsible,
    add_student,
    db_id,
)

TODAY = date(2027, 3, 10)
PHONE = '62988880001'


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dashboard_module, 'local_today', lambda: TODAY)
    monkeypatch.setattr(incomplete_module, 'local_today', lambda: TODAY)


async def _ids(db_session: AsyncSession, kind: str) -> set[int]:
    return await incomplete_student_ids(
        db_session, SEED.academy_id, kind, TODAY
    )


async def _student(db_session: AsyncSession, public_id: str) -> int:
    return await db_id(db_session, Student, public_id)


@pytest.mark.asyncio
async def test_responsible_phone_is_enough(db_session: AsyncSession):
    tkd = await add_modality(db_session, 'Taekwondo')
    with_mother, _ = await add_student(db_session, tkd, 'Ana')
    await add_responsible(db_session, with_mother, phone=PHONE)
    alone, _ = await add_student(db_session, tkd, 'Bruno')
    own, _ = await add_student(db_session, tkd, 'Caio', phone=PHONE)

    assert await _ids(db_session, 'no_phone') == {
        await _student(db_session, alone)
    }
    assert await _student(db_session, own) not in await _ids(
        db_session, 'no_phone'
    )


@pytest.mark.asyncio
async def test_minor_without_responsible(db_session: AsyncSession):
    tkd = await add_modality(db_session, 'Taekwondo')
    alone, _ = await add_student(
        db_session, tkd, 'Ana', birth_date='2015-05-01'
    )
    with_mother, _ = await add_student(
        db_session, tkd, 'Bia', birth_date='2015-05-01'
    )
    await add_responsible(db_session, with_mother)
    await add_student(db_session, tkd, 'Caio')  # sem data de nascimento
    await add_student(db_session, tkd, 'Davi', birth_date='1990-01-01')

    assert await _ids(db_session, 'minor_without_responsible') == {
        await _student(db_session, alone)
    }


@pytest.mark.asyncio
async def test_no_birth_date_and_no_email(db_session: AsyncSession):
    tkd = await add_modality(db_session, 'Taekwondo')
    no_birth, _ = await add_student(
        db_session, tkd, 'Ana', email='ana@gmail.com'
    )
    with_birth, _ = await add_student(
        db_session, tkd, 'Bia', birth_date='1990-01-01'
    )

    assert await _ids(db_session, 'no_birth_date') == {
        await _student(db_session, no_birth)
    }
    assert await _ids(db_session, 'no_email') == {
        await _student(db_session, with_birth)
    }


@pytest.mark.asyncio
async def test_inactive_students_ignored(db_session: AsyncSession):
    tkd = await add_modality(db_session, 'Taekwondo')
    await add_student(
        db_session, tkd, 'Saiu', 'inactive', birth_date='2015-05-01'
    )

    for kind in (
        'no_phone',
        'no_birth_date',
        'no_email',
        'minor_without_responsible',
    ):
        assert await _ids(db_session, kind) == set()


@pytest.mark.asyncio
async def test_students_list_incomplete_filter(
    client: AsyncClient, db_session: AsyncSession
):
    tkd = await add_modality(db_session, 'Taekwondo')
    await add_student(db_session, tkd, 'Ana')
    await add_student(db_session, tkd, 'Bia', birth_date='1990-01-01')

    response = await client.get(
        '/api/v1/students',
        headers=await auth_headers(client),
        params={'incomplete': 'no_birth_date'},
    )

    assert response.status_code == HTTPStatus.OK, response.text
    assert [s['name'] for s in response.json()['items']] == ['Ana']


@pytest.mark.asyncio
async def test_summary_incomplete_counts(
    client: AsyncClient, db_session: AsyncSession
):
    tkd = await add_modality(db_session, 'Taekwondo')
    await add_student(db_session, tkd, 'Ana', birth_date='2015-05-01')
    await add_student(
        db_session,
        tkd,
        'Bia',
        phone=PHONE,
        email='bia@gmail.com',
        birth_date='1990-01-01',
    )

    response = await client.get(
        '/api/v1/dashboard/summary', headers=await auth_headers(client)
    )

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['incomplete'] == {
        'no_phone': 1,
        'no_birth_date': 0,
        'no_email': 1,
        'minor_without_responsible': 1,
    }
