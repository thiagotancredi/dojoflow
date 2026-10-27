"""Tarefas do worker.

Cada tarefa é uma função comum (o Celery não roda código async); o
trabalho de verdade fica num núcleo async, chamado por ``run_async``. Os
testes chamam o núcleo direto.
"""

import logging
from datetime import date

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.integrations.email.sender import (
    EmailUnavailable,
    get_email_sender,
)
from dojoflow.integrations.infinitepay.client import (
    InfinitePayClient,
    InfinitePayUnavailable,
)
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import BillingService
from dojoflow.services.email_billing import EmailBillingService
from dojoflow.services.infinitepay import InfinitePayService
from dojoflow.services.password_reset import PasswordResetService
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


async def send_monthly_billing_emails_job(
    session: AsyncSession, today: date
) -> list[int]:
    """Alunos que ainda recebem a cobrança do mês por e-mail."""
    return await EmailBillingService(session).due_recipients(today)


@celery_app.task(name='dojoflow.send_monthly_billing_emails')
def send_monthly_billing_emails() -> int:
    """Dia 1º às 8h: uma tarefa de envio por aluno."""
    today = local_today()
    student_ids = run_async(
        lambda session: send_monthly_billing_emails_job(session, today)
    )
    for student_id in student_ids:
        # O dia vai junto: uma nova tentativa no dia 2 ainda é a cobrança
        # do mês certo
        send_billing_email.delay(student_id, today.isoformat())

    logger.info(
        '%s e-mail(s) de cobrança na fila para %s.', len(student_ids), today
    )
    return len(student_ids)


@celery_app.task(
    name='dojoflow.send_billing_email',
    # SES fora do ar ou no limite, ou banco fora do ar: tenta de novo
    autoretry_for=(EmailUnavailable, DBAPIError),
    # 1 s, 2 s, 4 s… até 1 h entre tentativas (cerca de 2 h no total)
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=False,
    max_retries=12,
    # Abaixo do limite de envio do SES
    rate_limit='10/s',
)
def send_billing_email(student_id: int, day: str) -> str | None:
    """Envia a cobrança do mês para um aluno (uma vez só)."""
    today = date.fromisoformat(day)
    sender = get_email_sender()
    status = run_async(
        lambda session: EmailBillingService(session).send_to_student(
            student_id, today, sender
        )
    )
    logger.info('Billing e-mail for student %s: %s.', student_id, status)
    return status.value if status else None


@celery_app.task(
    name='dojoflow.send_password_reset_email',
    # SES fora do ar ou no limite, ou banco fora do ar: tenta de novo
    autoretry_for=(EmailUnavailable, DBAPIError),
    # 1 s, 2 s, 4 s… até 1 h entre tentativas (cerca de 2 h no total)
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=False,
    max_retries=12,
    # Abaixo do limite de envio do SES
    rate_limit='10/s',
)
def send_password_reset_email(email: str) -> str | None:
    """Manda o link de nova senha, se a conta existir e puder receber."""
    sender = get_email_sender()
    status = run_async(
        lambda session: PasswordResetService(session).send_reset_email(
            email, sender
        )
    )
    # Sem e-mail no log: o pedido não pode revelar se a conta existe
    logger.info('Password reset e-mail: %s.', status)
    return status.value if status else None
