from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

UNIT_OF_WORK_DEPTH_KEY = 'unit_of_work_depth'


def in_unit_of_work(db_session: AsyncSession) -> bool:
    return db_session.info.get(UNIT_OF_WORK_DEPTH_KEY, 0) > 0


@asynccontextmanager
async def unit_of_work(
    db_session: AsyncSession,
) -> AsyncGenerator[None, None]:
    depth = db_session.info.get(UNIT_OF_WORK_DEPTH_KEY, 0)
    db_session.info[UNIT_OF_WORK_DEPTH_KEY] = depth + 1

    try:
        yield
    except BaseException:
        db_session.info[UNIT_OF_WORK_DEPTH_KEY] = depth

        if depth == 0:
            await db_session.rollback()

        raise

    db_session.info[UNIT_OF_WORK_DEPTH_KEY] = depth

    if depth == 0:
        await db_session.commit()


def transactional(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        async with unit_of_work(self.db_session):
            return await method(self, *args, **kwargs)

    return wrapper
