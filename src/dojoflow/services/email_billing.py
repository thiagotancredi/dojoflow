"""Cobrança por e-mail na academia: liga/desliga, prévia, contagem e o
envio do dia 1º (feito pelo worker)."""

import logging
from datetime import UTC, date, datetime

from botocore.exceptions import ClientError
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.database.transaction import transactional
from dojoflow.integrations.email.sender import EmailMessage, EmailSender
from dojoflow.models.academy import Academy
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from dojoflow.models.email_log import EmailLog
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.student import Student
from dojoflow.schemas.email_billing_api import (
    EmailBillingStatusApi,
    EmailPreviewApi,
)
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import (
    BillingService,
    Contact,
    StudentContact,
    choose_email_recipient,
    pay_url,
)
from dojoflow.services.email_templates import billing_email
from dojoflow.shared.enums import (
    AcademyStatus,
    EmailKind,
    EmailStatus,
    EnrollmentStatus,
)
from dojoflow.shared.exceptions import ConflictError

logger = logging.getLogger(__name__)

NOT_CONFIGURED_MESSAGE = (
    'Configure a chave Pix ou ligue a InfinitePay antes de ligar a '
    'cobrança por e-mail.'
)
PREVIEW_STUDENT_NAME = 'Lucas'
PREVIEW_TOKEN = 'exemplo'  # noqa: S105
# Tamanho da coluna email_log.error
ERROR_MAX_LENGTH = 500
# Mesma condição do índice único parcial uq_email_log_billing_student_month
BILLING_INDEX_WHERE = text("kind = 'billing'")


def _first_name(*names: str) -> str:
    """Primeiro nome do primeiro nome preenchido."""
    for name in names:
        if name.split():
            return name.split()[0]
    return ''


class EmailBillingService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.billing = BillingService(db_session=db_session)

    async def _enabled(self, academy_id: int) -> bool:
        return bool(
            await self.db_session.scalar(
                select(AcademyBillingSettings.email_billing_enabled).where(
                    AcademyBillingSettings.academy_id == academy_id
                )
            )
        )

    async def _charged_student_ids(
        self, academy_id: int, student_ids: set[int] | None = None
    ) -> set[int]:
        """Alunos com matrícula ativa e não isenta (só entre os dados, se
        vier a lista)."""
        stmt = select(Enrollment.student_id).where(
            Enrollment.academy_id == academy_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
            Enrollment.is_exempt.is_(False),
        )
        if student_ids is not None:
            stmt = stmt.where(Enrollment.student_id.in_(student_ids))
        return set(await self.db_session.scalars(stmt.distinct()))

    async def students_without_email_ids(self, academy_id: int) -> set[int]:
        """Alunos ativos e não isentos que ficariam sem receber o e-mail."""
        charged = await self._charged_student_ids(academy_id)
        contacts = await self.billing.contacts(academy_id, charged)
        today = local_today()

        return {
            student_id
            for student_id, contact in contacts.items()
            if choose_email_recipient(contact, today) is None
        }

    async def status(self, academy_id: int) -> EmailBillingStatusApi:
        return EmailBillingStatusApi(
            enabled=await self._enabled(academy_id),
            can_enable=await self.billing.billing_configured(academy_id),
            students_without_email=len(
                await self.students_without_email_ids(academy_id)
            ),
        )

    @transactional
    async def set_enabled(
        self, academy_id: int, enabled: bool
    ) -> EmailBillingStatusApi:
        if enabled and not await self.billing.billing_configured(academy_id):
            raise ConflictError(
                NOT_CONFIGURED_MESSAGE, code='BILLING_NOT_CONFIGURED'
            )

        await self.db_session.execute(
            insert(AcademyBillingSettings)
            .values(academy_id=academy_id, email_billing_enabled=enabled)
            .on_conflict_do_update(
                index_elements=[AcademyBillingSettings.academy_id],
                set_={'email_billing_enabled': enabled},
            )
        )

        return await self.status(academy_id)

    async def preview(self, academy_id: int) -> EmailPreviewApi:
        """O e-mail como o aluno vai ver, assinado pelo mestre da academia."""
        master, _ = await self.billing.academy_master(academy_id)
        rendered = billing_email(
            recipient_first_name=PREVIEW_STUDENT_NAME,
            academy=await self.billing.academy_name(academy_id),
            master=master,
            pay_link=pay_url(PREVIEW_TOKEN),
        )

        return EmailPreviewApi(subject=rendered.subject, html=rendered.html)

    async def _sends_billing_emails(self, academy_id: int) -> bool:
        """Academia ativa, com o e-mail ligado e a cobrança configurada."""
        status = await self.db_session.scalar(
            select(Academy.status).where(Academy.id == academy_id)
        )
        return (
            status is AcademyStatus.ACTIVE
            and await self._enabled(academy_id)
            and await self.billing.billing_configured(academy_id)
        )

    async def _due_contacts(
        self, academy_id: int, student_ids: set[int], today: date
    ) -> dict[int, tuple[StudentContact, Contact]]:
        """Dos alunos dados, os que recebem: ativos, não isentos, com algo
        em aberto (o mesmo da /pagar) e com e-mail. Valor: (aluno, quem
        recebe)."""
        if not student_ids:
            return {}

        charged = await self._charged_student_ids(academy_id, student_ids)
        contacts = await self.billing.contacts(academy_id, charged)
        due = {}

        for student_id in sorted(contacts):
            contact = contacts[student_id]
            recipient = choose_email_recipient(contact, today)
            if (
                recipient is not None
                and await self.billing.payable_for_student(
                    academy_id, student_id, today
                )
            ):
                due[student_id] = (contact, recipient)

        return due

    async def _due_recipient(
        self, academy_id: int, student_id: int, today: date
    ) -> tuple[StudentContact, Contact] | None:
        """Confere, na hora do envio, se o aluno ainda deve receber."""
        if not await self._sends_billing_emails(academy_id):
            return None
        due = await self._due_contacts(academy_id, {student_id}, today)
        return due.get(student_id)

    async def due_recipients(self, today: date) -> list[int]:
        """Alunos que recebem a cobrança do mês e ainda não receberam."""
        month = today.replace(day=1)
        academy_ids = await self.db_session.scalars(
            select(AcademyBillingSettings.academy_id)
            .where(AcademyBillingSettings.email_billing_enabled.is_(True))
            .order_by(AcademyBillingSettings.academy_id)
        )
        # Enviado ou falha final: não entra de novo no mês
        done = set(
            await self.db_session.scalars(
                select(EmailLog.student_id).where(
                    EmailLog.kind == EmailKind.BILLING,
                    EmailLog.reference_month == month,
                    EmailLog.status.in_([
                        EmailStatus.SENT,
                        EmailStatus.FAILED,
                    ]),
                )
            )
        )
        due: list[int] = []

        for academy_id in list(academy_ids):
            if not await self._sends_billing_emails(academy_id):
                continue
            pending = await self._charged_student_ids(academy_id) - done
            due.extend(await self._due_contacts(academy_id, pending, today))

        return due

    async def _reserve(
        self, academy_id: int, student_id: int, month: date
    ) -> EmailLog | None:
        """Reserva o envio do mês na trava única do email_log.

        Linha já existente fica travada até o fim da transação (um envio
        simultâneo do mesmo aluno espera aqui). None quando o e-mail do mês
        já foi enviado ou falhou de vez.
        """
        await self.db_session.execute(
            insert(EmailLog)
            .values(
                kind=EmailKind.BILLING,
                status=EmailStatus.PENDING,
                academy_id=academy_id,
                student_id=student_id,
                # Preenchido logo antes do envio
                recipient='',
                reference_month=month,
            )
            .on_conflict_do_nothing(
                index_elements=[EmailLog.student_id, EmailLog.reference_month],
                index_where=BILLING_INDEX_WHERE,
            )
        )
        log = await self.db_session.scalar(
            select(EmailLog)
            .where(
                EmailLog.kind == EmailKind.BILLING,
                EmailLog.student_id == student_id,
                EmailLog.reference_month == month,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        # pending: sobra de um envio interrompido, reaproveita
        if log is None or log.status is not EmailStatus.PENDING:
            return None
        return log

    @transactional
    async def send_to_student(
        self, student_id: int, today: date, sender: EmailSender
    ) -> EmailStatus | None:
        """Envia a cobrança do mês para o aluno, uma vez só.

        Tudo numa transação: SES fora do ar (``EmailUnavailable``) desfaz a
        reserva e sobe o erro, para o Celery tentar de novo. Outro erro do
        SES grava ``failed`` e termina sem erro. None quando não há o que
        enviar (já enviado, pago, academia desligada, sem e-mail).
        """
        academy_id = await self.db_session.scalar(
            select(Student.academy_id).where(Student.id == student_id)
        )
        if academy_id is None:
            return None

        log = await self._reserve(academy_id, student_id, today.replace(day=1))
        if log is None:
            return None

        # O aluno pode ter pago (ou a academia desligado) depois da lista
        due = await self._due_recipient(academy_id, student_id, today)
        if due is None:
            await self.db_session.delete(log)
            return None

        contact, recipient = due
        master, master_email = await self.billing.academy_master(academy_id)
        academy = await self.billing.academy_name(academy_id)
        rendered = billing_email(
            recipient_first_name=_first_name(recipient.name, contact.name),
            academy=academy,
            master=master,
            pay_link=pay_url(contact.pay_token),
        )
        log.recipient = (recipient.email or '').strip()

        try:
            message_id = sender.send(
                EmailMessage(
                    to=log.recipient,
                    subject=rendered.subject,
                    html=rendered.html,
                    text=rendered.text,
                    from_name=academy,
                    from_address=settings.EMAIL_FROM_BILLING,
                    reply_to=master_email or None,
                )
            )
        except ClientError as error:
            logger.warning(
                'Billing e-mail rejected (student_id=%s): %s',
                student_id,
                error,
            )
            log.status = EmailStatus.FAILED
            log.error = str(error)[:ERROR_MAX_LENGTH]
            return EmailStatus.FAILED

        log.status = EmailStatus.SENT
        log.provider_message_id = message_id
        log.sent_at = datetime.now(UTC)
        return EmailStatus.SENT
