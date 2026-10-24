"""App Celery do worker.

Rodar (o beat vai embutido, por isso uma réplica só):
    celery -A dojoflow.worker.app worker -B --loglevel=INFO
"""

from typing import Any

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

from dojoflow.core.settings import settings

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
    beat_schedule={
        # Dia 1º: gera às 00:05 e confere às 02:05, 04:05 e 06:05 (cria só
        # o que faltar)
        'generate-monthly-charges': {
            'task': 'dojoflow.generate_monthly_charges',
            'schedule': crontab(minute=5, hour='0,2,4,6', day_of_month=1),
        },
    },
)


@worker_ready.connect
def check_charges_on_startup(sender: Any, **kwargs: Any) -> None:
    """Conferência ao ligar: cobre o worker desligado na madrugada do 1º."""
    from dojoflow.worker.tasks import generate_monthly_charges  # noqa: PLC0415

    generate_monthly_charges.delay()
