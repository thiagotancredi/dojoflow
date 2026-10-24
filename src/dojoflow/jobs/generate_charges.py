"""Comando manual de emergência: cria as mensalidades que faltam.

Quem gera normalmente é o worker (dia 1º e ao ligar; ver
dojoflow.worker.tasks). Use só se o worker estiver fora do ar:
    poetry run python -m dojoflow.jobs.generate_charges
"""

import asyncio

from dojoflow.database.session import AsyncSessionLocal, engine
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import BillingService


async def run() -> int:
    try:
        async with AsyncSessionLocal() as session:
            return await BillingService(session).ensure_monthly_charges(
                None, local_today()
            )
    finally:
        await engine.dispose()


if __name__ == '__main__':
    created = asyncio.run(run())
    print(f'{created} mensalidade(s) criada(s).')
