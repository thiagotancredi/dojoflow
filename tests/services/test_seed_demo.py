import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.commands.seed_demo import (
    KB,
    TKD,
    check_target,
    ensure_modalities,
    seed,
)
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.belt import Belt
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from tests.helpers.auth import SEED


def test_check_target_dev_needs_no_confirmation():
    check_target('Dojo Teste', None, 'dev')


def test_check_target_prod_requires_confirmation():
    with pytest.raises(SystemExit):
        check_target('Katsuflow', None, 'prod')


def test_check_target_prod_rejects_other_academy():
    with pytest.raises(SystemExit):
        check_target('Academia de Cliente', 'Katsuflow', 'prod')


def test_check_target_prod_accepts_matching_name():
    check_target('Katsuflow', '  katsuflow ', 'prod')


def test_check_target_unknown_academy():
    with pytest.raises(SystemExit):
        check_target(None, 'Katsuflow', 'prod')


async def _catalog(session: AsyncSession) -> None:
    session.add_all([
        Modality(name=TKD, emoji='🥋', is_active=True),
        Modality(name=KB, emoji='🥊', is_active=True),
    ])
    await session.commit()


@pytest.mark.asyncio
async def test_ensure_modalities_enables_with_belts(db_session: AsyncSession):
    await _catalog(db_session)

    found = await ensure_modalities(db_session, SEED.academy_id)
    again = await ensure_modalities(db_session, SEED.academy_id)
    await db_session.commit()

    assert set(found) == {TKD, KB}
    assert again == found
    links = await db_session.scalar(
        select(func.count()).select_from(AcademyModality)
    )
    assert links == 2  # noqa: PLR2004
    for modality_id in found.values():
        belts = await db_session.scalar(
            select(func.count()).where(
                Belt.academy_id == SEED.academy_id,
                Belt.modality_id == modality_id,
            )
        )
        assert belts > 0


@pytest.mark.asyncio
async def test_seed_runs_on_academy_without_modalities(
    db_session: AsyncSession,
):
    await _catalog(db_session)

    created = await seed(db_session, SEED.academy_id, {})
    await db_session.commit()

    students = await db_session.scalar(
        select(func.count()).where(Student.academy_id == SEED.academy_id)
    )
    assert created > 0
    assert students == created
