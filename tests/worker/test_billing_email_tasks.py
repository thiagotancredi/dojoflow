import asyncio
from datetime import date, datetime

import pytest
from botocore.exceptions import ClientError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dojoflow.core.settings import settings
from dojoflow.integrations.email.sender import (
    ConsoleEmailSender,
    EmailMessage,
    EmailUnavailable,
)
from dojoflow.models.academy import Academy
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from dojoflow.models.email_log import EmailLog
from dojoflow.models.master import Master
from dojoflow.models.payment import Payment
from dojoflow.models.student import Student
from dojoflow.services import email_billing as email_billing_module
from dojoflow.services.billing import pay_url
from dojoflow.services.email_billing import EmailBillingService
from dojoflow.shared.enums import (
    EmailKind,
    EmailStatus,
    PaymentStatus,
    PixKeyType,
)
from dojoflow.worker import app as worker_app
from dojoflow.worker import tasks
from tests.helpers.auth import SEED
from tests.helpers.scenario import (
    add_modality,
    add_responsible,
    add_student,
    generate_charges,
)

TODAY = date(2027, 3, 1)
MONTH = date(2027, 3, 1)


async def _configure(
    session: AsyncSession,
    academy_id: int | None = None,
    *,
    enabled: bool = True,
    pix: bool = True,
) -> None:
    session.add(
        AcademyBillingSettings(
            academy_id=academy_id or SEED.academy_id,
            pix_key='dojo@exemplo.com' if pix else None,
            pix_key_type=PixKeyType.EMAIL if pix else None,
            pix_city='Goiânia' if pix else None,
            email_billing_enabled=enabled,
        )
    )
    await session.commit()


async def _academy(
    session: AsyncSession, name: str, master_email: str | None
) -> int:
    academy = Academy(name=name)
    session.add(academy)
    await session.flush()
    session.add(
        Master(academy_id=academy.id, name='Mestre Dois', email=master_email)
    )
    await session.commit()
    return academy.id


async def _student(  # noqa: PLR0913
    session: AsyncSession,
    modality: str,
    name: str,
    email: str | None,
    *,
    academy_id: int | None = None,
    monthly_fee: str | None = '100',
    **kwargs: object,
) -> int:
    """Aluno com mensalidade de março (vence dia 10) e e-mail próprio."""
    public_id, _ = await add_student(
        session,
        modality,
        name,
        monthly_fee=monthly_fee,
        due_day=10 if monthly_fee else None,
        billing_start_month='2027-03-01' if monthly_fee else None,
        academy_id=academy_id,
        **kwargs,
    )
    await session.execute(
        update(Student)
        .where(Student.public_id == public_id)
        .values(email=email)
    )
    await session.commit()
    return await session.scalar(
        select(Student.id).where(Student.public_id == public_id)
    )


async def _run_flow(
    session: AsyncSession, sender: ConsoleEmailSender, today: date = TODAY
) -> list[EmailStatus | None]:
    """Faz o papel do worker: lista quem recebe e envia um por um."""
    service = EmailBillingService(session)
    return [
        await service.send_to_student(student_id, today, sender)
        for student_id in await tasks.send_monthly_billing_emails_job(
            session, today
        )
    ]


async def _logs(session: AsyncSession) -> list[EmailLog]:
    return list(
        await session.scalars(
            select(EmailLog)
            .order_by(EmailLog.id)
            .execution_options(populate_existing=True)
        )
    )


class _FailingSender:
    def __init__(self, error: Exception, failing_to: str | None = None):
        self.error = error
        self.failing_to = failing_to
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> str:
        if self.failing_to in {None, message.to}:
            raise self.error
        self.sent.append(message)
        return f'ok-{len(self.sent)}'


def _rejected() -> ClientError:
    return ClientError(
        {
            'Error': {
                'Code': 'MessageRejected',
                'Message': 'Email address is not verified.',
            },
            'ResponseMetadata': {'HTTPStatusCode': 400},
        },
        'SendEmail',
    )


@pytest.mark.asyncio
async def test_sends_only_for_enabled_academies_with_open_amount(
    db_session: AsyncSession,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    await _student(
        db_session, judo, 'Bia Isenta', 'bia@exemplo.com', is_exempt=True
    )
    await _student(
        db_session, judo, 'Caio Inativo', 'caio@exemplo.com', status='inactive'
    )
    await _student(
        db_session, judo, 'Duda Em Dia', 'duda@exemplo.com', monthly_fee=None
    )
    await _student(db_session, judo, 'Edu Sem Email', None)

    # Academia desligada e academia ligada mas sem cobrança configurada
    off = await _academy(db_session, 'Dojo Desligado', 'off@exemplo.com')
    await _configure(db_session, off, enabled=False)
    no_pix = await _academy(db_session, 'Dojo Sem Pix', 'nopix@exemplo.com')
    await _configure(db_session, no_pix, pix=False)
    for academy_id, modality_name, email in (
        (off, 'Karatê', 'fabio@exemplo.com'),
        (no_pix, 'Muay Thai', 'gil@exemplo.com'),
    ):
        modality = await add_modality(db_session, modality_name, academy_id)
        await _student(
            db_session, modality, 'Fulano', email, academy_id=academy_id
        )

    await generate_charges(db_session, TODAY)
    sender = ConsoleEmailSender()

    statuses = await _run_flow(db_session, sender)

    assert statuses == [EmailStatus.SENT]
    assert [m.to for m in sender.sent] == ['ana@exemplo.com']
    (log,) = await _logs(db_session)
    assert log.kind is EmailKind.BILLING
    assert log.status is EmailStatus.SENT
    assert log.recipient == 'ana@exemplo.com'
    assert log.reference_month == MONTH
    assert log.provider_message_id == 'console-1'
    assert log.sent_at is not None


@pytest.mark.asyncio
async def test_minor_with_own_email_and_responsible_without_email_gets_own(
    db_session: AsyncSession,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    student_id = await _student(
        db_session,
        judo,
        'Lucas Prado',
        '  lucas@exemplo.com ',
        birth_date='2015-05-20',
    )
    public_id = await db_session.scalar(
        select(Student.public_id).where(Student.id == student_id)
    )
    await add_responsible(db_session, str(public_id), 'Maria Prado')
    await generate_charges(db_session, TODAY)
    sender = ConsoleEmailSender()

    await _run_flow(db_session, sender)

    (message,) = sender.sent
    assert message.to == 'lucas@exemplo.com'
    assert 'Olá, Lucas!' in message.text


@pytest.mark.asyncio
async def test_resend_after_restart_does_not_duplicate(
    db_session: AsyncSession,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    ana = await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    bia = await _student(db_session, judo, 'Bia Reis', 'bia@exemplo.com')
    caio = await _student(db_session, judo, 'Caio Dias', 'caio@exemplo.com')
    await generate_charges(db_session, TODAY)
    sender = ConsoleEmailSender()

    # Antes de o worker cair: Ana recebeu; Bia ficou com o envio no meio
    await EmailBillingService(db_session).send_to_student(ana, TODAY, sender)
    db_session.add(
        EmailLog(
            kind=EmailKind.BILLING,
            status=EmailStatus.PENDING,
            academy_id=SEED.academy_id,
            student_id=bia,
            recipient='bia@exemplo.com',
            reference_month=MONTH,
        )
    )
    await db_session.commit()

    # Worker religado: roda o fluxo inteiro, e depois roda de novo
    await _run_flow(db_session, sender)
    await _run_flow(db_session, sender)

    assert sorted(m.to for m in sender.sent) == [
        'ana@exemplo.com',
        'bia@exemplo.com',
        'caio@exemplo.com',
    ]
    logs = await _logs(db_session)
    assert sorted(log.student_id for log in logs) == sorted([ana, bia, caio])
    assert {log.status for log in logs} == {EmailStatus.SENT}
    assert await tasks.send_monthly_billing_emails_job(db_session, TODAY) == []


@pytest.mark.asyncio
async def test_two_sends_at_once_for_same_student_send_one_email(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    ana = await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    await generate_charges(db_session, TODAY)
    sender = ConsoleEmailSender()

    # Segura a trava por um instante, para o outro envio chegar nela
    original = EmailBillingService._due_recipient

    async def slow_due_recipient(self, *args, **kwargs):
        await asyncio.sleep(0.2)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(
        EmailBillingService, '_due_recipient', slow_due_recipient
    )
    make_session = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def send() -> EmailStatus | None:
        async with make_session() as session:
            return await EmailBillingService(session).send_to_student(
                ana, TODAY, sender
            )

    statuses = await asyncio.gather(send(), send())

    assert sorted(statuses, key=str) == sorted(
        [EmailStatus.SENT, None], key=str
    )
    assert len(sender.sent) == 1
    assert len(await _logs(db_session)) == 1


@pytest.mark.asyncio
async def test_ses_unavailable_raises_and_leaves_no_sent_row(
    db_session: AsyncSession,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    ana = await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    await generate_charges(db_session, TODAY)
    service = EmailBillingService(db_session)

    with pytest.raises(EmailUnavailable):
        await service.send_to_student(
            ana, TODAY, _FailingSender(EmailUnavailable('SES fora'))
        )

    assert await _logs(db_session) == []
    assert await service.due_recipients(TODAY) == [ana]

    # A nova tentativa do Celery, com o SES de volta, envia
    sender = ConsoleEmailSender()
    status = await service.send_to_student(ana, TODAY, sender)

    assert status is EmailStatus.SENT
    assert len(sender.sent) == 1


@pytest.mark.asyncio
async def test_ses_rejected_marks_failed_and_continues(
    db_session: AsyncSession,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    await _student(db_session, judo, 'Bia Reis', 'bia@exemplo.com')
    await generate_charges(db_session, TODAY)
    sender = _FailingSender(_rejected(), failing_to='ana@exemplo.com')

    statuses = await _run_flow(db_session, sender)

    assert statuses == [EmailStatus.FAILED, EmailStatus.SENT]
    assert [m.to for m in sender.sent] == ['bia@exemplo.com']
    failed, sent = await _logs(db_session)
    assert failed.status is EmailStatus.FAILED
    assert 'MessageRejected' in failed.error
    assert failed.sent_at is None
    assert sent.status is EmailStatus.SENT
    # Falha final não volta para a lista (nem trava o resto)
    assert await tasks.send_monthly_billing_emails_job(db_session, TODAY) == []


@pytest.mark.asyncio
async def test_paid_before_retry_is_not_sent(db_session: AsyncSession):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    ana = await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    await generate_charges(db_session, TODAY)
    service = EmailBillingService(db_session)
    assert await service.due_recipients(TODAY) == [ana]

    # Pagou entre a lista das 8h e o envio
    await db_session.execute(
        update(Payment).values(
            amount_paid=Payment.amount_due, status=PaymentStatus.PAID
        )
    )
    await db_session.commit()
    sender = ConsoleEmailSender()

    status = await service.send_to_student(ana, TODAY, sender)

    assert status is None
    assert sender.sent == []
    assert await _logs(db_session) == []


@pytest.mark.asyncio
async def test_academy_disabled_after_listing_is_not_sent(
    db_session: AsyncSession,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    ana = await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    await generate_charges(db_session, TODAY)
    service = EmailBillingService(db_session)
    assert await service.due_recipients(TODAY) == [ana]

    await db_session.execute(
        update(AcademyBillingSettings).values(email_billing_enabled=False)
    )
    await db_session.commit()
    sender = ConsoleEmailSender()

    status = await service.send_to_student(ana, TODAY, sender)

    assert status is None
    assert sender.sent == []
    assert await _logs(db_session) == []


@pytest.mark.asyncio
async def test_from_name_is_academy_and_reply_to_is_master_email(
    db_session: AsyncSession,
):
    await _configure(db_session)
    judo = await add_modality(db_session, 'Judô')
    ana = await _student(db_session, judo, 'Ana Lima', 'ana@exemplo.com')
    other = await _academy(db_session, 'Dojo "Tigre" São José', None)
    await _configure(db_session, other)
    karate = await add_modality(db_session, 'Karatê', other)
    await _student(
        db_session, karate, 'Bia Reis', 'bia@exemplo.com', academy_id=other
    )
    await generate_charges(db_session, TODAY)
    sender = ConsoleEmailSender()

    await _run_flow(db_session, sender)

    ana_message, bia_message = sender.sent
    token = await db_session.scalar(
        select(Student.pay_token).where(Student.id == ana)
    )
    assert ana_message.from_name == SEED.academy_name
    assert ana_message.from_address == settings.EMAIL_FROM_BILLING
    assert ana_message.reply_to == SEED.email
    assert ana_message.subject == (
        f'Mensalidade disponível — {SEED.academy_name}'
    )
    assert pay_url(token) in ana_message.text
    assert SEED.master_name in ana_message.text
    # Mestre sem e-mail: sem Reply-To
    assert bia_message.from_name == 'Dojo "Tigre" São José'
    assert bia_message.reply_to is None


def test_should_catch_up_billing_emails() -> None:
    catch_up = worker_app.should_catch_up_billing_emails

    assert catch_up(datetime(2026, 11, 1, 7, 59)) is False
    assert catch_up(datetime(2026, 11, 1, 8, 0)) is True
    assert catch_up(datetime(2026, 11, 2, 23, 0)) is True
    assert catch_up(datetime(2026, 11, 3, 9, 0)) is False


class _FakeChain:
    def __init__(self, *signatures: object) -> None:
        self.signatures = signatures
        self.delayed = False

    def delay(self) -> None:
        self.delayed = True


def test_startup_catch_up_chains_charges_then_emails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chains: list[_FakeChain] = []
    delays: list[str] = []

    def fake_chain(*signatures: object) -> _FakeChain:
        chains.append(_FakeChain(*signatures))
        return chains[-1]

    monkeypatch.setattr(worker_app, 'chain', fake_chain)
    monkeypatch.setattr(
        tasks.generate_monthly_charges,
        'delay',
        lambda: delays.append('charges'),
    )

    monkeypatch.setattr(
        worker_app, 'should_catch_up_billing_emails', lambda now: True
    )
    worker_app.check_charges_on_startup(sender=None)
    monkeypatch.setattr(
        worker_app, 'should_catch_up_billing_emails', lambda now: False
    )
    worker_app.check_charges_on_startup(sender=None)

    (startup_chain,) = chains
    assert startup_chain.delayed is True
    assert [s.task for s in startup_chain.signatures] == [
        'dojoflow.generate_monthly_charges',
        'dojoflow.send_monthly_billing_emails',
    ]
    # .si(): a lista de e-mails não recebe o resultado da geração
    assert all(s.immutable for s in startup_chain.signatures)
    # Fora do dia 1º/2: só a geração, como antes
    assert delays == ['charges']


def test_send_billing_email_task_retries_on_unavailable() -> None:
    task = tasks.send_billing_email

    assert task.name == 'dojoflow.send_billing_email'
    assert EmailUnavailable in task.autoretry_for
    assert task.retry_backoff is True
    assert task.retry_backoff_max == 3600  # noqa: PLR2004
    assert task.max_retries == 12  # noqa: PLR2004
    assert task.rate_limit == '10/s'
    assert task.acks_late is True


def test_send_billing_email_task_targets_the_given_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, date]] = []

    async def fake_send(self, student_id, today, sender):
        calls.append((student_id, today))
        return EmailStatus.SENT

    monkeypatch.setattr(
        email_billing_module.EmailBillingService, 'send_to_student', fake_send
    )

    # Nova tentativa no dia 2 ainda conta como a cobrança de março
    result = tasks.send_billing_email(7, '2027-03-01')

    assert calls == [(7, date(2027, 3, 1))]
    assert result == 'sent'
