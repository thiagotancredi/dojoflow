"""Cobrança por e-mail na academia: liga/desliga, prévia e contagem."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from dojoflow.models.enrollment import Enrollment
from dojoflow.schemas.email_billing_api import (
    EmailBillingStatusApi,
    EmailPreviewApi,
)
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import (
    BillingService,
    choose_email_recipient,
    pay_url,
)
from dojoflow.services.email_templates import billing_email
from dojoflow.shared.enums import EnrollmentStatus
from dojoflow.shared.exceptions import ConflictError

NOT_CONFIGURED_MESSAGE = (
    'Configure a chave Pix ou ligue a InfinitePay antes de ligar a '
    'cobrança por e-mail.'
)
PREVIEW_STUDENT_NAME = 'Lucas'
PREVIEW_TOKEN = 'exemplo'  # noqa: S105


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

    async def students_without_email_ids(self, academy_id: int) -> set[int]:
        """Alunos ativos e não isentos que ficariam sem receber o e-mail."""
        charged = set(
            await self.db_session.scalars(
                select(Enrollment.student_id)
                .where(
                    Enrollment.academy_id == academy_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                    Enrollment.is_exempt.is_(False),
                )
                .distinct()
            )
        )
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
