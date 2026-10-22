"""Dashboard: faixa etária, aniversariantes e novos alunos por mês."""

from datetime import UTC, date, datetime
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.services import dashboard as dashboard_module
from dojoflow.shared.enums import EnrollmentStatus
from tests.helpers.auth import SEED, auth_headers, other_academy_headers
from tests.helpers.scenario import add_modality, add_student

URL = '/api/v1/dashboard/summary'
TODAY = date(2027, 3, 10)


@pytest.fixture(autouse=True)
def _fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dashboard_module, 'local_today', lambda: TODAY)


async def _summary(client: AsyncClient) -> dict:
    response = await client.get(URL, headers=await auth_headers(client))
    assert response.status_code == HTTPStatus.OK

    return response.json()


async def _student_id(db_session: AsyncSession, public_id: str) -> int:
    student = await db_session.scalar(
        select(Student).where(Student.public_id == public_id)
    )
    assert student is not None

    return student.id


async def _add_enrollment(
    db_session: AsyncSession,
    student_public_id: str,
    modality_public_id: str,
    created_at: datetime | None = None,
) -> None:
    """Segunda matrícula para um aluno que já existe."""
    modality = await db_session.scalar(
        select(Modality).where(Modality.public_id == modality_public_id)
    )
    assert modality is not None
    db_session.add(
        Enrollment(
            academy_id=SEED.academy_id,
            student_id=await _student_id(db_session, student_public_id),
            modality_id=modality.id,
            status=EnrollmentStatus.ACTIVE,
            is_exempt=True,
            **({'created_at': created_at} if created_at else {}),
        )
    )
    await db_session.commit()


async def _set_created_at(
    db_session: AsyncSession,
    enrollment_public_id: str,
    moment: datetime,
) -> None:
    await db_session.execute(
        update(Enrollment)
        .where(Enrollment.public_id == enrollment_public_id)
        .values(created_at=moment)
    )
    await db_session.commit()


def _groups(items: list[dict]) -> dict[str, int]:
    return {item['group']: item['count'] for item in items}


@pytest.mark.asyncio
async def test_age_groups_boundaries_and_unknown(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    tkd = await add_modality(db_session, 'Taekwondo')
    # Hoje é 10/03/2027: quem nasceu em 10/03 já fez aniversário
    births = {
        'Doze': '2014-03-11',  # 12 → kids
        'Treze': '2014-03-10',  # 13 → juvenile
        'Dezessete': '2009-03-11',  # 17 → juvenile
        'Dezoito': '2009-03-10',  # 18 → adult
        'Trinta e nove': '1987-03-11',  # 39 → adult
        'Quarenta': '1987-03-10',  # 40 → master
    }
    for name, birth in births.items():
        await add_student(db_session, tkd, name, birth_date=birth)
    await add_student(db_session, tkd, 'Sem data')
    await add_student(
        db_session, tkd, 'Inativo', status='inactive', birth_date='2015-01-01'
    )

    body = await _summary(client)

    assert body['age_groups']['all'] == [
        {'group': 'kids', 'count': 1},
        {'group': 'juvenile', 'count': 2},
        {'group': 'adult', 'count': 2},
        {'group': 'master', 'count': 1},
        {'group': 'unknown', 'count': 1},
    ]


@pytest.mark.asyncio
async def test_age_groups_by_modality(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    tkd = await add_modality(db_session, 'Taekwondo')
    kick = await add_modality(db_session, 'Kickboxing')
    both, _ = await add_student(
        db_session, tkd, 'Nos dois', birth_date='2017-01-01'
    )
    await _add_enrollment(db_session, both, kick)
    await add_student(db_session, kick, 'Adulto', birth_date='1990-01-01')

    body = await _summary(client)

    assert _groups(body['age_groups']['all']) == {
        'kids': 1,
        'juvenile': 0,
        'adult': 1,
        'master': 0,
        'unknown': 0,
    }
    by_modality = {
        item['modality_name']: _groups(item['groups'])
        for item in body['age_groups']['by_modality']
    }
    assert [i['modality_name'] for i in body['age_groups']['by_modality']] == [
        'Kickboxing',
        'Taekwondo',
    ]
    assert by_modality['Kickboxing']['kids'] == 1
    assert by_modality['Kickboxing']['adult'] == 1
    assert by_modality['Taekwondo']['kids'] == 1
    assert by_modality['Taekwondo']['adult'] == 0


@pytest.mark.asyncio
async def test_birthdays_of_the_month(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    tkd = await add_modality(db_session, 'Taekwondo')
    await add_student(db_session, tkd, 'Carla', birth_date='2000-03-25')
    await add_student(db_session, tkd, 'Ana', birth_date='2016-03-10')
    await add_student(db_session, tkd, 'Bruno', birth_date='1995-03-05')
    await add_student(db_session, tkd, 'Abril', birth_date='2000-04-02')
    await add_student(
        db_session, tkd, 'Inativa', status='inactive', birth_date='2000-03-11'
    )
    await add_student(db_session, tkd, 'Sem data')

    body = await _summary(client)

    assert [
        (b['name'], b['day'], b['turning_age'], b['is_today'])
        for b in body['birthdays']
    ] == [
        ('Bruno', 5, 32, False),
        ('Ana', 10, 11, True),
        ('Carla', 25, 27, False),
    ]


@pytest.mark.asyncio
async def test_leap_day_birthday_shows_on_feb_28(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dashboard_module, 'local_today', lambda: date(2027, 2, 28)
    )
    tkd = await add_modality(db_session, 'Taekwondo')
    await add_student(db_session, tkd, 'Bissexto', birth_date='2000-02-29')

    body = await _summary(client)

    assert [
        (b['day'], b['turning_age'], b['is_today']) for b in body['birthdays']
    ] == [(28, 27, True)]


@pytest.mark.asyncio
async def test_new_students_by_month_last_6_months(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    tkd = await add_modality(db_session, 'Taekwondo')
    kick = await add_modality(db_session, 'Kickboxing')

    _, march = await add_student(db_session, tkd, 'Março')
    await _set_created_at(
        db_session, march, datetime(2027, 3, 2, 12, tzinfo=UTC)
    )
    # Janeiro no Taekwondo e, depois, Kickboxing em março: conta só janeiro
    january_student, january = await add_student(db_session, tkd, 'Janeiro')
    await _set_created_at(
        db_session, january, datetime(2027, 1, 15, 12, tzinfo=UTC)
    )
    await _add_enrollment(
        db_session,
        january_student,
        kick,
        created_at=datetime(2027, 3, 5, 12, tzinfo=UTC),
    )
    # 01/11 às 01:30 UTC = 31/10 às 22:30 em Brasília: conta em outubro
    _, october = await add_student(db_session, tkd, 'Outubro')
    await _set_created_at(
        db_session, october, datetime(2026, 11, 1, 1, 30, tzinfo=UTC)
    )
    # Setembro: fora da janela de 6 meses
    _, september = await add_student(db_session, tkd, 'Setembro')
    await _set_created_at(
        db_session, september, datetime(2026, 9, 20, 12, tzinfo=UTC)
    )
    # Aluno que já saiu continua contando no mês em que entrou
    _, left = await add_student(db_session, tkd, 'Saiu', status='inactive')
    await _set_created_at(
        db_session, left, datetime(2026, 12, 5, 12, tzinfo=UTC)
    )

    body = await _summary(client)

    assert body['new_students_by_month'] == [
        {'month': '2026-10-01', 'count': 1},
        {'month': '2026-11-01', 'count': 0},
        {'month': '2026-12-01', 'count': 1},
        {'month': '2027-01-01', 'count': 1},
        {'month': '2027-02-01', 'count': 0},
        {'month': '2027-03-01', 'count': 1},
    ]


@pytest.mark.asyncio
async def test_insights_are_isolated_per_academy(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await other_academy_headers(db_session)
    other = await db_session.scalar(
        select(Academy).where(Academy.name == 'Outra Academia')
    )
    assert other is not None
    judo = await add_modality(db_session, 'Judô', academy_id=other.id)
    await add_student(
        db_session,
        judo,
        'De outra academia',
        birth_date='2000-03-12',
        academy_id=other.id,
    )

    body = await _summary(client)

    assert body['birthdays'] == []
    assert _groups(body['age_groups']['all'])['adult'] == 0
    assert body['age_groups']['by_modality'] == []
    assert sum(m['count'] for m in body['new_students_by_month']) == 0
