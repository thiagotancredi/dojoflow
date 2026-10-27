import re
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.rate_limit import password_reset_limiter
from dojoflow.integrations.email.sender import ConsoleEmailSender
from dojoflow.models.email_log import EmailLog
from dojoflow.models.master import Master
from dojoflow.models.one_time_token import OneTimeToken
from dojoflow.services.password_reset import (
    PURPOSE_PASSWORD_RESET,
    PasswordResetService,
)
from dojoflow.shared.enums import EmailKind, EmailStatus
from dojoflow.worker import tasks
from tests.helpers.auth import SEED
from tests.helpers.onboarding import register_web

REQUEST_URL = '/api/v1/auth/password-reset/request'
CONFIRM_URL = '/api/v1/auth/password-reset/confirm'
LOGIN_URL = '/api/v1/auth/login'
REFRESH_URL = '/api/v1/auth/refresh'
MAX_PER_HOUR = 3
NEW_PASSWORD = 'senha-nova-123'  # noqa: S105


@pytest.fixture(autouse=True)
def _reset_limiter() -> None:
    password_reset_limiter.reset()


async def _send(
    session: AsyncSession, email: str = SEED.email
) -> tuple[EmailStatus | None, ConsoleEmailSender]:
    sender = ConsoleEmailSender()
    status = await PasswordResetService(session).send_reset_email(
        email, sender
    )
    return status, sender


def _token_of(sender: ConsoleEmailSender) -> str:
    match = re.search(r'/redefinir-senha/([\w-]+)', sender.sent[-1].text)
    assert match
    return match.group(1)


async def _tokens(session: AsyncSession) -> list[OneTimeToken]:
    return list(
        await session.scalars(
            select(OneTimeToken)
            .where(OneTimeToken.purpose == PURPOSE_PASSWORD_RESET)
            .order_by(OneTimeToken.id)
            .execution_options(populate_existing=True)
        )
    )


@pytest.mark.asyncio
async def test_request_always_202_same_body(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        tasks.send_password_reset_email, 'delay', calls.append
    )

    known = await client.post(REQUEST_URL, json={'email': SEED.email})
    unknown = await client.post(REQUEST_URL, json={'email': 'x@nada.test'})

    assert known.status_code == unknown.status_code == HTTPStatus.ACCEPTED
    assert known.json() == unknown.json() == {'status': 'sent'}
    # A rota só enfileira: nada de consulta ao banco
    assert calls == [SEED.email, 'x@nada.test']


@pytest.mark.asyncio
async def test_request_normalizes_email(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        tasks.send_password_reset_email, 'delay', calls.append
    )
    await client.post(REQUEST_URL, json={'email': f' {SEED.email.upper()} '})
    assert calls == [SEED.email]

    status, sender = await _send(db_session, f' {SEED.email.upper()} ')

    assert status is EmailStatus.SENT
    assert sender.sent[0].to == SEED.email
    assert sender.sent[0].from_name == 'Katsuflow'
    log = (await db_session.scalars(select(EmailLog))).one()
    assert log.kind is EmailKind.PASSWORD_RESET
    assert log.master_id == SEED.master_id


@pytest.mark.asyncio
async def test_unknown_or_passwordless_account_sends_nothing(
    db_session: AsyncSession,
) -> None:
    status, sender = await _send(db_session, 'x@nada.test')
    assert status is None
    assert sender.sent == []

    await db_session.execute(
        update(Master)
        .where(Master.id == SEED.master_id)
        .values(password_hash=None)
    )
    await db_session.commit()
    try:
        status, sender = await _send(db_session)
        assert status is None
        assert sender.sent == []
        assert await _tokens(db_session) == []
    finally:
        await db_session.execute(
            update(Master)
            .where(Master.id == SEED.master_id)
            .values(password_hash=SEED.password_hash)
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_confirm_sets_password_and_revokes_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    response, payload = await register_web(client)
    old_refresh = response.cookies['dojoflow_refresh']
    _, sender = await _send(db_session, payload['email'])

    confirm = await client.post(
        CONFIRM_URL,
        json={'token': _token_of(sender), 'password': NEW_PASSWORD},
    )

    assert confirm.status_code == HTTPStatus.NO_CONTENT
    new_login = await client.post(
        LOGIN_URL, json={'email': payload['email'], 'password': NEW_PASSWORD}
    )
    assert new_login.status_code == HTTPStatus.OK
    old_login = await client.post(
        LOGIN_URL,
        json={'email': payload['email'], 'password': payload['password']},
    )
    assert old_login.status_code == HTTPStatus.UNAUTHORIZED

    client.cookies.clear()
    client.cookies.set('dojoflow_refresh', old_refresh)
    refresh = await client.post(REFRESH_URL)
    assert refresh.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_token_single_use_and_expires(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, sender = await _send(db_session)
    token = _token_of(sender)
    body = {'token': token, 'password': NEW_PASSWORD}

    first = await client.post(CONFIRM_URL, json=body)
    second = await client.post(CONFIRM_URL, json=body)

    assert first.status_code == HTTPStatus.NO_CONTENT
    assert second.status_code == HTTPStatus.UNAUTHORIZED
    assert second.json()['code'] == 'RESET_LINK_INVALID'

    # Restaura a senha do mestre fixo para os outros testes
    await db_session.execute(
        update(Master)
        .where(Master.id == SEED.master_id)
        .values(password_hash=SEED.password_hash)
    )
    await db_session.commit()

    _, sender = await _send(db_session)
    await db_session.execute(
        update(OneTimeToken)
        .where(OneTimeToken.token == _token_of(sender))
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db_session.commit()
    expired = await client.post(
        CONFIRM_URL,
        json={'token': _token_of(sender), 'password': NEW_PASSWORD},
    )
    assert expired.status_code == HTTPStatus.UNAUTHORIZED
    assert expired.json()['code'] == 'RESET_LINK_INVALID'


@pytest.mark.asyncio
async def test_new_request_invalidates_previous_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, first = await _send(db_session)
    _, second = await _send(db_session)

    old = await client.post(
        CONFIRM_URL,
        json={'token': _token_of(first), 'password': NEW_PASSWORD},
    )
    assert old.status_code == HTTPStatus.UNAUTHORIZED

    new = await client.post(
        CONFIRM_URL,
        json={'token': _token_of(second), 'password': NEW_PASSWORD},
    )
    assert new.status_code == HTTPStatus.NO_CONTENT

    await db_session.execute(
        update(Master)
        .where(Master.id == SEED.master_id)
        .values(password_hash=SEED.password_hash)
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_more_than_three_requests_per_hour_are_ignored(
    db_session: AsyncSession,
) -> None:
    results = [(await _send(db_session)) for _ in range(4)]

    assert [status for status, _ in results] == [
        EmailStatus.SENT,
        EmailStatus.SENT,
        EmailStatus.SENT,
        None,
    ]
    assert results[3][1].sent == []
    assert len(await _tokens(db_session)) == MAX_PER_HOUR
    logs = (await db_session.scalars(select(EmailLog))).all()
    assert len(logs) == MAX_PER_HOUR


@pytest.mark.asyncio
async def test_password_too_short_422(client: AsyncClient) -> None:
    response = await client.post(
        CONFIRM_URL, json={'token': 'abc', 'password': '1234567'}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_rate_limited_429(client: AsyncClient) -> None:
    body = {'token': 'abc', 'password': NEW_PASSWORD}
    statuses = [
        (await client.post(CONFIRM_URL, json=body)).status_code
        for _ in range(6)
    ]

    assert statuses[:5] == [HTTPStatus.UNAUTHORIZED] * 5
    assert statuses[5] == HTTPStatus.TOO_MANY_REQUESTS
