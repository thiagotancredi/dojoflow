from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def verify_transaction(
    db_session: AsyncSession,
) -> AsyncGenerator[None, None]:
    if db_session.in_transaction():
        yield
        return

    async with db_session.begin():
        yield


def transactional(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        db_session: AsyncSession = self.db_session

        async with verify_transaction(db_session):
            return await method(self, *args, **kwargs)

    return wrapper
