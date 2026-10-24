"""Tarefas do worker.

Cada tarefa é uma função comum (o Celery não roda código async); o
trabalho de verdade fica num núcleo async, chamado por ``run_async``. Os
testes chamam o núcleo direto.
"""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import BillingService
from dojoflow.worker.app import celery_app
from dojoflow.worker.bridge import run_async

logger = logging.getLogger(__name__)


async def generate_monthly_charges_job(
    session: AsyncSession, today: date
) -> int:
    """Cria as mensalidades que faltam, de todas as academias."""
    return await BillingService(session).ensure_monthly_charges(None, today)


@celery_app.task(name='dojoflow.generate_monthly_charges')
def generate_monthly_charges() -> int:
    today = local_today()
    created = run_async(
        lambda session: generate_monthly_charges_job(session, today)
    )
    logger.info('%s mensalidade(s) criada(s) para %s.', created, today)
    return created
