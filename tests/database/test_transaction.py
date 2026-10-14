import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import in_unit_of_work, unit_of_work
from dojoflow.models.modality import Modality
from dojoflow.repositories.modality import ModalityRepository


async def _committed_modality_count(db_session: AsyncSession) -> int:
    async with AsyncSession(bind=db_session.bind) as other_session:
        return await other_session.scalar(
            select(func.count()).select_from(Modality)
        )


def _modality_data(name: str) -> dict[str, object]:
    return {'name': name, 'emoji': '🥋', 'is_active': True}


@pytest.mark.asyncio
async def test_write_outside_unit_of_work_raises(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    with pytest.raises(RuntimeError, match='unit of work'):
        await repository.create(_modality_data('Judô'))


@pytest.mark.asyncio
async def test_outermost_unit_of_work_commits(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    async with unit_of_work(db_session):
        await repository.create(_modality_data('Judô'))

    assert await _committed_modality_count(db_session) == 1
    assert in_unit_of_work(db_session) is False


@pytest.mark.asyncio
async def test_nested_unit_of_work_commits_only_at_outermost(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    async with unit_of_work(db_session):
        async with unit_of_work(db_session):
            await repository.create(_modality_data('Judô'))

        assert await _committed_modality_count(db_session) == 0

    assert await _committed_modality_count(db_session) == 1


@pytest.mark.asyncio
async def test_exception_rolls_back_outermost_unit_of_work(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    with pytest.raises(ValueError, match='boom'):  # noqa: PT012
        async with unit_of_work(db_session):
            await repository.create(_modality_data('Judô'))
            raise ValueError('boom')

    assert await _committed_modality_count(db_session) == 0
    assert in_unit_of_work(db_session) is False


@pytest.mark.asyncio
async def test_commits_even_after_implicit_read_transaction(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    await db_session.execute(select(Modality))
    assert db_session.in_transaction() is True

    async with unit_of_work(db_session):
        await repository.create(_modality_data('Judô'))

    assert await _committed_modality_count(db_session) == 1
