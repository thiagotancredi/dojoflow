"""Ponte entre as tarefas do Celery (funções comuns) e o código async."""

import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.session import AsyncSessionLocal, engine


def run_async[T](make_coro: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Abre uma sessão, roda a corrotina, confirma e fecha as conexões.

    Cada chamada tem o próprio laço de eventos (``asyncio.run``); por isso
    as conexões do engine são descartadas no fim, para não serem
    reaproveitadas num laço que já acabou.
    """

    async def main() -> T:
        try:
            async with AsyncSessionLocal() as session:
                result = await make_coro(session)
                await session.commit()
                return result
        finally:
            await engine.dispose()

    return asyncio.run(main())
