from dojoflow.integrations.infinitepay.client import InfinitePayUnavailable
from dojoflow.worker import tasks


def test_settle_task_retries_on_unavailable() -> None:
    task = tasks.settle_infinitepay_payment

    assert InfinitePayUnavailable in task.autoretry_for
    assert task.max_retries == 10  # noqa: PLR2004
    assert task.retry_backoff is True
    # Avisos repetidos: a tarefa pode rodar de novo sem dano
    assert task.acks_late is True
