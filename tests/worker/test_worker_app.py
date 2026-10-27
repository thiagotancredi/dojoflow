from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.worker.app import celery_app
from dojoflow.worker.bridge import run_async

ANSWER = 42


def test_celery_app_config() -> None:
    assert celery_app.conf.broker_url == settings.REDIS_URL
    assert celery_app.conf.timezone == 'America/Sao_Paulo'
    assert celery_app.conf.enable_utc is False
    assert celery_app.conf.task_acks_late is True


def test_run_async_runs_coroutine() -> None:
    # Síncrono de propósito: a ponte abre o próprio laço de eventos
    async def answer(session: AsyncSession) -> int:
        assert isinstance(session, AsyncSession)
        return ANSWER

    assert run_async(answer) == ANSWER
