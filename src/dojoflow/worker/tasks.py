"""Tarefas do worker.

Cada tarefa é uma função comum (o Celery não roda código async); o
trabalho de verdade fica num núcleo async, chamado por ``run_async``. Os
testes chamam o núcleo direto.
"""

import logging
from datetime import date

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.integrations.infinitepay.client import (
    InfinitePayClient,
    InfinitePayUnavailable,
)
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import BillingService
from dojoflow.services.infinitepay import InfinitePayService
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


@celery_app.task(
    name='dojoflow.settle_infinitepay_payment',
    # InfinitePay ou banco fora do ar (ou deadlock): tenta de novo
    autoretry_for=(InfinitePayUnavailable, DBAPIError),
    # 1 s, 2 s, 4 s… até 1 h entre tentativas, por cerca de 20 h: o aviso
    # já teve resposta 200, então a InfinitePay não manda de novo
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=False,
    max_retries=30,
)
def settle_infinitepay_payment(
    order_nsu: str,
    transaction_nsu: str,
    slug: str,
    receipt_url: str | None = None,
    student_id: int | None = None,
) -> str | None:
    """Confere o pagamento na InfinitePay e dá a baixa (uma vez só).

    InfinitePay fora do ar: tenta de novo mais tarde, com espera crescente.
    """
    status = run_async(
        lambda session: InfinitePayService(
            session, InfinitePayClient()
        ).settle(
            order_nsu,
            transaction_nsu,
            slug,
            receipt_url=receipt_url,
            student_id=student_id,
        )
    )
    logger.info('InfinitePay settlement finished: %s.', status)
    return status.value if status else None
