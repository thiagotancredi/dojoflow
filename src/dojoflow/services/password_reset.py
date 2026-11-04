"""Recuperar senha: pedido (feito pelo worker) e troca da senha."""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from botocore.exceptions import ClientError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.database.transaction import transactional
from dojoflow.integrations.email.sender import EmailMessage, EmailSender
from dojoflow.models.email_log import EmailLog
from dojoflow.models.master import Master
from dojoflow.repositories.one_time_token import OneTimeTokenRepository
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from dojoflow.services.email_templates import password_reset_email
from dojoflow.services.security import hash_password
from dojoflow.shared.enums import EmailKind, EmailStatus
from dojoflow.shared.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)

PURPOSE_PASSWORD_RESET = 'password_reset'  # noqa: S105
PASSWORD_RESET_TTL = timedelta(minutes=30)
MAX_REQUESTS_PER_HOUR = 3
SENDER_NAME = 'Katsuflow'
# Tamanho da coluna email_log.error
ERROR_MAX_LENGTH = 500


class PasswordResetService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.tokens = OneTimeTokenRepository(db_session=db_session)
        self.sessions = RefreshSessionRepository(db_session=db_session)

    async def _master_id_by_email(self, email: str) -> int | None:
        """Conta com esse e-mail (sem diferença de maiúsculas) e senha."""
        return await self.db_session.scalar(
            select(Master.id).where(
                func.lower(Master.email) == email.strip().lower(),
                Master.password_hash.is_not(None),
            )
        )

    @transactional
    async def send_reset_email(
        self, email: str, sender: EmailSender
    ) -> EmailStatus | None:
        """Manda o link de nova senha. Sem conta, ou com pedidos demais na
        última hora, termina em silêncio (None).

        Tudo numa transação: ``EmailUnavailable`` desfaz o código novo e
        sobe o erro, para o Celery tentar de novo.
        """
        master_id = await self._master_id_by_email(email)
        if master_id is None:
            return None

        now = datetime.now(UTC)
        recent = await self.tokens.count_created_since(
            master_id, PURPOSE_PASSWORD_RESET, now - timedelta(hours=1)
        )
        if recent >= MAX_REQUESTS_PER_HOUR:
            return None

        # Pedido novo invalida o anterior
        await self.tokens.invalidate_open(master_id, PURPOSE_PASSWORD_RESET)
        token = secrets.token_urlsafe(16)
        await self.tokens.create({
            'master_id': master_id,
            'token': token,
            'purpose': PURPOSE_PASSWORD_RESET,
            'expires_at': now + PASSWORD_RESET_TTL,
            'used_at': None,
            'academy_id': None,
        })

        recipient = email.strip().lower()
        log = EmailLog(
            kind=EmailKind.PASSWORD_RESET,
            status=EmailStatus.PENDING,
            master_id=master_id,
            recipient=recipient,
        )
        self.db_session.add(log)
        rendered = password_reset_email(
            reset_link=f'{settings.WEB_APP_URL}/redefinir-senha/{token}'
        )

        try:
            message_id = sender.send(
                EmailMessage(
                    to=recipient,
                    subject=rendered.subject,
                    html=rendered.html,
                    text=rendered.text,
                    from_name=SENDER_NAME,
                    from_address=settings.EMAIL_FROM_ACCOUNT,
                )
            )
        except ClientError as error:
            logger.warning(
                'Password reset e-mail rejected (master_id=%s): %s',
                master_id,
                error,
            )
            log.status = EmailStatus.FAILED
            log.error = str(error)[:ERROR_MAX_LENGTH]
            return EmailStatus.FAILED

        log.status = EmailStatus.SENT
        log.provider_message_id = message_id
        log.sent_at = datetime.now(UTC)
        return EmailStatus.SENT

    @transactional
    async def confirm(self, token: str, password: str) -> None:
        """Troca a senha com o código de uso único e encerra as sessões."""
        master_id = await self.tokens.consume_valid(
            token, PURPOSE_PASSWORD_RESET
        )
        if master_id is None:
            raise UnauthorizedError(
                'Invalid or expired token.', code='RESET_LINK_INVALID'
            )

        await self.db_session.execute(
            update(Master)
            .where(Master.id == master_id)
            .values(password_hash=hash_password(password))
        )
        await self.sessions.revoke_all_for_master(
            master_id=master_id, revoked_at=datetime.now(UTC)
        )
