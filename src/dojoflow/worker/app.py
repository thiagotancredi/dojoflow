"""App Celery do worker.

Rodar (o beat vai embutido, por isso uma réplica só):
    celery -A dojoflow.worker.app worker -B --loglevel=INFO
"""

from celery import Celery

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
)
