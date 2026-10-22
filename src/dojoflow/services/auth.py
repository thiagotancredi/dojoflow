import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.database.transaction import transactional
from dojoflow.repositories.audit_log import AuditLogRepository
from dojoflow.repositories.one_time_token import OneTimeTokenRepository
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from dojoflow.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResult,
    AuthTokenResponse,
    SetCredentialsRequest,
    SupportEntryRead,
)
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.schemas.onboarding import OnboardingWebCreate
from dojoflow.services.admin_access import is_admin_email
from dojoflow.services.master import MasterService
from dojoflow.services.onboarding import OnboardingService
from dojoflow.services.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from dojoflow.shared.enums import AcademyStatus, AuditAction
from dojoflow.shared.exceptions import (
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
)

PURPOSE_SUPPORT_ENTRY = 'support_entry'
SUPPORT_CODE_TTL = timedelta(seconds=60)
SUPPORT_SESSION_TTL = timedelta(hours=8)
REFRESH_REUSE_GRACE_SECONDS = 30
REFRESH_CHAIN_MAX_HOPS = 20


def ensure_academy_active(context: MasterContextRead) -> None:
    if context.academy_status == AcademyStatus.BLOCKED:
        raise UnauthorizedError('Academy is blocked.', code='ACADEMY_BLOCKED')


class AuthService:
    def __init__(
        self,
        onboarding_service: OnboardingService,
        master_service: MasterService,
        one_time_token_repository: OneTimeTokenRepository,
        refresh_session_repository: RefreshSessionRepository,
        db_session: AsyncSession,
    ) -> None:
        self.onboarding_service = onboarding_service
        self.master_service = master_service
        self.one_time_token_repository = one_time_token_repository
        self.refresh_session_repository = refresh_session_repository
        self.db_session = db_session

    async def register(
        self,
        data: AuthRegisterRequest,
    ) -> AuthResult:
        if is_admin_email(str(data.email)):
            raise ConflictError(
                'This email is reserved.', code='ADMIN_EMAIL_RESERVED'
            )

        onboarding = await self.onboarding_service.register_web(
            OnboardingWebCreate(
                academy_name=data.academy_name,
                master_name=data.master_name,
                email=str(data.email),
                password=data.password,
                phone=data.phone,
            )
        )

        context = await self.master_service.get_context_by_id(
            onboarding.master_id
        )

        if context is None:
            raise UnauthorizedError('Could not load master context.')

        return await self._start_session(context)

    async def login(
        self,
        data: AuthLoginRequest,
    ) -> AuthResult:
        normalized_email = str(data.email).strip().lower()
        master = await self.master_service.get_by_email(normalized_email)

        if master is None or master.get('password_hash') is None:
            raise UnauthorizedError(
                'Invalid email or password.',
                code='INVALID_CREDENTIALS',
            )

        if not verify_password(data.password, str(master['password_hash'])):
            raise UnauthorizedError(
                'Invalid email or password.',
                code='INVALID_CREDENTIALS',
            )

        master_id = int(master['id'])
        context = await self.master_service.get_context_by_id(master_id)

        if context is None:
            raise UnauthorizedError(
                'Invalid email or password.',
                code='INVALID_CREDENTIALS',
            )

        ensure_academy_active(context)

        return await self._start_session(context)

    async def refresh(self, refresh_token: str) -> AuthResult:
        session = await self.refresh_session_repository.get_by_token_hash(
            hash_refresh_token(refresh_token)
        )
        now = datetime.now(UTC)

        if session is None or session['expires_at'] <= now:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        if session['revoked_at'] is None:
            return await self._rotate_session(session)

        if session['replaced_by_id'] is None:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        master_id = int(session['master_id'])
        grace = timedelta(seconds=REFRESH_REUSE_GRACE_SECONDS)

        if now - session['revoked_at'] > grace:
            await self.revoke_all_sessions(master_id)
            raise UnauthorizedError(
                'Refresh token was already used.',
                code='REFRESH_TOKEN_REUSED',
            )

        tail = await self._find_active_chain_tail(session)

        if tail is None:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        return await self._start_session_for_master(
            master_id, **self._support_scope(tail)
        )

    @transactional
    async def logout(self, refresh_token: str | None) -> None:
        if refresh_token is None:
            return

        session = await self.refresh_session_repository.get_by_token_hash(
            hash_refresh_token(refresh_token)
        )

        if session is None or session['revoked_at'] is not None:
            return

        await self.refresh_session_repository.update_by_id(
            record_id=int(session['id']),
            data={'revoked_at': datetime.now(UTC)},
        )

    @transactional
    async def revoke_all_sessions(self, master_id: int) -> None:
        await self.refresh_session_repository.revoke_all_for_master(
            master_id=master_id,
            revoked_at=datetime.now(UTC),
        )

    async def _find_active_chain_tail(
        self,
        session: dict[str, Any],
    ) -> dict[str, Any] | None:
        current = session

        for _ in range(REFRESH_CHAIN_MAX_HOPS):
            if current['replaced_by_id'] is None:
                return current if current['revoked_at'] is None else None

            next_session = await self.refresh_session_repository.get_by_id(
                int(current['replaced_by_id'])
            )

            if next_session is None:
                return None

            current = next_session

        return None

    @staticmethod
    def _support_scope(session: dict[str, Any]) -> dict[str, Any]:
        """Sessão de suporte renova na mesma academia e no mesmo prazo."""
        if session.get('acting_academy_id') is None:
            return {}

        return {
            'acting_academy_id': int(session['acting_academy_id']),
            'expires_at': session['expires_at'],
        }

    @transactional
    async def _rotate_session(self, session: dict[str, Any]) -> AuthResult:
        result, new_session_id = await self._create_session(
            int(session['master_id']), **self._support_scope(session)
        )

        await self.refresh_session_repository.update_by_id(
            record_id=int(session['id']),
            data={
                'revoked_at': datetime.now(UTC),
                'replaced_by_id': new_session_id,
            },
        )

        return result

    @transactional
    async def _start_session_for_master(
        self,
        master_id: int,
        *,
        acting_academy_id: int | None = None,
        expires_at: datetime | None = None,
    ) -> AuthResult:
        result, _ = await self._create_session(
            master_id,
            acting_academy_id=acting_academy_id,
            expires_at=expires_at,
        )

        return result

    async def _start_session(self, context: MasterContextRead) -> AuthResult:
        return await self._start_session_for_master(context.master_id)

    async def _create_session(
        self,
        master_id: int,
        *,
        acting_academy_id: int | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[AuthResult, int]:
        if acting_academy_id is None:
            context = await self.master_service.get_context_by_id(master_id)
        else:
            context = await self.master_service.get_support_context(
                master_id, acting_academy_id
            )

        if context is None:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        if acting_academy_id is None:
            ensure_academy_active(context)
        elif not is_admin_email(context.email):
            raise UnauthorizedError(
                'Support session is no longer valid.',
                code='SUPPORT_SESSION_INVALID',
            )

        refresh_token = generate_refresh_token()
        session_id = await self.refresh_session_repository.create({
            'master_id': master_id,
            'token_hash': hash_refresh_token(refresh_token),
            'expires_at': expires_at
            or datetime.now(UTC)
            + timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
            'acting_academy_id': acting_academy_id,
        })

        response = AuthTokenResponse(
            access_token=create_access_token(master_id, acting_academy_id),
        )

        return AuthResult(response, refresh_token), session_id

    @transactional
    async def set_credentials(
        self,
        data: SetCredentialsRequest,
        *,
        authenticated_master_id: int | None = None,
    ) -> AuthResult:
        if authenticated_master_id is not None:
            master = await self.master_service.get_by_id(
                authenticated_master_id
            )
            password_hash = master.get('password_hash') if master else None

            if password_hash is not None and (
                data.current_password is None
                or not verify_password(
                    data.current_password,
                    str(password_hash),
                )
            ):
                raise ForbiddenError(
                    'Current password is invalid.',
                    code='CURRENT_PASSWORD_INVALID',
                )

            master_id = authenticated_master_id
        else:
            raise UnauthorizedError('Authentication required.')

        context = await self.master_service.set_credentials(
            master_id=master_id,
            email=str(data.email),
            password_hash=hash_password(data.password),
        )

        await self.revoke_all_sessions(master_id)

        return await self._start_session(context)

    @transactional
    async def _issue_one_time_token(
        self,
        master_id: int,
        purpose: str,
        ttl: timedelta,
        academy_id: int | None = None,
    ) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(16)
        expires_at = datetime.now(UTC) + ttl

        await self.one_time_token_repository.create({
            'master_id': master_id,
            'token': token,
            'purpose': purpose,
            'expires_at': expires_at,
            'used_at': None,
            'academy_id': academy_id,
        })

        return token, expires_at

    @transactional
    async def _consume_one_time_token_record(
        self,
        token: str,
        purpose: str,
        *,
        error_code: str,
    ) -> dict[str, Any]:
        record = await self.one_time_token_repository.get_valid_by_token(
            token=token,
            purpose=purpose,
        )

        if record is None:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code=error_code,
            )

        await self.one_time_token_repository.update_by_id(
            record_id=int(record['id']),
            data={'used_at': datetime.now(UTC)},
        )

        return record

    @transactional
    async def create_support_entry(
        self,
        admin_master_id: int,
        academy_id: int,
    ) -> SupportEntryRead:
        """Código de uso único para abrir o modo suporte numa aba nova."""
        code, expires_at = await self._issue_one_time_token(
            master_id=admin_master_id,
            purpose=PURPOSE_SUPPORT_ENTRY,
            ttl=SUPPORT_CODE_TTL,
            academy_id=academy_id,
        )
        await AuditLogRepository(db_session=self.db_session).create({
            'academy_id': academy_id,
            'master_id': admin_master_id,
            'action': AuditAction.SUPPORT_ENTRY,
            'entity_name': 'academy',
            'entity_id': academy_id,
            'description': 'Support mode entry',
        })

        return SupportEntryRead(code=code, expires_at=expires_at)

    @transactional
    async def exchange_support_code(self, code: str) -> AuthResult:
        record = await self._consume_one_time_token_record(
            code, PURPOSE_SUPPORT_ENTRY, error_code='SUPPORT_CODE_INVALID'
        )

        if record.get('academy_id') is None:
            raise UnauthorizedError(
                'Invalid or expired token.', code='SUPPORT_CODE_INVALID'
            )

        result, _ = await self._create_session(
            int(record['master_id']),
            acting_academy_id=int(record['academy_id']),
            expires_at=datetime.now(UTC) + SUPPORT_SESSION_TTL,
        )

        return result
