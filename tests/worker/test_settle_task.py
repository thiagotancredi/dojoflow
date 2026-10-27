from sqlalchemy.exc import DBAPIError

from dojoflow.integrations.infinitepay.client import InfinitePayUnavailable
from dojoflow.worker import tasks
from dojoflow.worker.app import celery_app


def test_settle_task_retries_on_unavailable() -> None:
    task = tasks.settle_infinitepay_payment

    assert InfinitePayUnavailable in task.autoretry_for
    # Banco fora do ar ou deadlock também tenta de novo
    assert DBAPIError in task.autoretry_for
    assert task.retry_backoff is True
    # Espera crescente até 1 h, por cerca de um dia: uma InfinitePay fora
    # do ar por horas não perde o aviso
    assert task.retry_backoff_max == 3600  # noqa: PLR2004
    assert task.retry_jitter is False
    assert task.max_retries >= 24  # noqa: PLR2004
    # Avisos repetidos: a tarefa pode rodar de novo sem dano
    assert task.acks_late is True


def test_redis_visibility_timeout_exceeds_longest_retry_wait() -> None:
    # Tarefa esperando a próxima tentativa fica sem confirmação no Redis;
    # se o prazo dele for menor que a espera, ela é entregue de novo
    # (cópias que se multiplicam numa queda longa)
    timeout = celery_app.conf.broker_transport_options['visibility_timeout']

    assert timeout >= 2 * tasks.settle_infinitepay_payment.retry_backoff_max
