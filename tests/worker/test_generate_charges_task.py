from datetime import date
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.payment import Payment
from dojoflow.services import billing as billing_module
from dojoflow.worker import app as worker_app
from dojoflow.worker import tasks
from dojoflow.worker.app import celery_app
from tests.helpers.auth import auth_headers
from tests.helpers.scenario import add_modality, add_student


async def _payment_count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Payment))


@pytest.mark.asyncio
async def test_generate_job_creates_missing_months(
    db_session: AsyncSession,
):
    taekwondo = await add_modality(db_session, 'Taekwondo')
    await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=10,
        billing_start_month='2027-01-01',
    )

    created = await tasks.generate_monthly_charges_job(
        db_session, date(2027, 3, 1)
    )
    again = await tasks.generate_monthly_charges_job(
        db_session, date(2027, 3, 1)
    )

    # janeiro, fevereiro e março; a segunda rodada não cria nada
    assert created == 3  # noqa: PLR2004
    assert again == 0
    assert await _payment_count(db_session) == 3  # noqa: PLR2004


def test_beat_schedule_day_one_four_times() -> None:
    entry = celery_app.conf.beat_schedule['generate-monthly-charges']
    schedule = entry['schedule']

    assert entry['task'] == tasks.generate_monthly_charges.name
    assert schedule.minute == {5}
    assert schedule.hour == {0, 2, 4, 6}
    assert schedule.day_of_month == {1}
    assert schedule.month_of_year == set(range(1, 13))
    assert schedule.day_of_week == set(range(7))


def test_worker_ready_enqueues_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple] = []
    monkeypatch.setattr(
        tasks.generate_monthly_charges,
        'delay',
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    worker_app.check_charges_on_startup(sender=None)

    assert calls == [((), {})]


@pytest.mark.asyncio
async def test_student_billing_does_not_generate_charges(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    headers = await auth_headers(client)
    taekwondo = await add_modality(db_session, 'Taekwondo')
    student_id, _ = await add_student(
        db_session,
        taekwondo,
        monthly_fee='100',
        due_day=10,
        billing_start_month='2027-03-01',
    )
    monkeypatch.setattr(
        billing_module, 'local_today', lambda: date(2027, 3, 1)
    )

    response = await client.get(
        f'/api/v1/students/{student_id}/billing', headers=headers
    )

    # O worker ainda não gerou março: a ficha mostra o que existe, sem erro
    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['charges'] == []
    assert await _payment_count(db_session) == 0
