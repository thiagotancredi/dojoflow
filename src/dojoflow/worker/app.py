"""App Celery do worker.

Rodar (o beat vai embutido, por isso uma réplica só):
    celery -A dojoflow.worker.app worker -B --loglevel=INFO
"""

from datetime import datetime
from typing import Any

from celery import Celery, chain
from celery.schedules import crontab
from celery.signals import worker_ready

from dojoflow.core.settings import settings
from dojoflow.services.belt_rules import ACADEMY_TIMEZONE

BILLING_EMAIL_HOUR = 8
# Último dia em que a conferência ao ligar ainda manda os e-mails do mês
BILLING_EMAIL_LAST_CATCH_UP_DAY = 2

celery_app = Celery(
    'dojoflow',
    broker=settings.REDIS_URL,
    include=['dojoflow.worker.tasks'],
)
celery_app.conf.update(
    timezone='America/Sao_Paulo',
    enable_utc=False,
    # A tarefa só sai da fila depois de terminar: se o worker cair no
    # meio, ela roda de novo
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Tarefa aguardando nova tentativa (até 1 h) fica sem confirmação no
    # Redis; o prazo dele precisa ser maior, senão ela é entregue de novo
    broker_transport_options={'visibility_timeout': 4 * 3600},
    beat_schedule={
        # Dia 1º: gera às 00:05 e confere às 02:05, 04:05 e 06:05 (cria só
        # o que faltar)
        'generate-monthly-charges': {
            'task': 'dojoflow.generate_monthly_charges',
            'schedule': crontab(minute=5, hour='0,2,4,6', day_of_month=1),
        },
        # Dia 1º às 8h: cobrança do mês por e-mail
        'send-monthly-billing-emails': {
            'task': 'dojoflow.send_monthly_billing_emails',
            'schedule': crontab(
                minute=0, hour=BILLING_EMAIL_HOUR, day_of_month=1
            ),
        },
    },
)


def should_catch_up_billing_emails(now: datetime) -> bool:
    """Worker ligado no dia 1º a partir das 8h ou no dia 2: o envio das 8h
    pode ter ficado para trás."""
    if now.tzinfo is not None:
        now = now.astimezone(ACADEMY_TIMEZONE)
    return (
        now.day == 1 and now.hour >= BILLING_EMAIL_HOUR
    ) or now.day == BILLING_EMAIL_LAST_CATCH_UP_DAY


@worker_ready.connect
def check_charges_on_startup(sender: Any, **kwargs: Any) -> None:
    """Conferência ao ligar: cobre o worker desligado na madrugada do 1º
    (e, no dia 1º depois das 8h ou no dia 2, o envio dos e-mails)."""
    from dojoflow.worker.tasks import (  # noqa: PLC0415
        generate_monthly_charges,
        send_monthly_billing_emails,
    )

    if should_catch_up_billing_emails(datetime.now(ACADEMY_TIMEZONE)):
        # Em sequência: as mensalidades do mês existem antes dos e-mails
        chain(
            generate_monthly_charges.si(), send_monthly_billing_emails.si()
        ).delay()
    else:
        generate_monthly_charges.delay()
