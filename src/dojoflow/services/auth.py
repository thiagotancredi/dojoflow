import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.settings import settings
from dojoflow.database.transaction import transactional
from dojoflow.repositories.one_time_token import OneTimeTokenRepository
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from dojoflow.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResult,
    AuthTokenResponse,
    SetCredentialsRequest,
    TelegramLinkTokenResponse,
    TelegramSetupTokenResponse,
)
from dojoflow.schemas.master_context import (
    MasterContextApiRead,
    MasterContextRead,
)
from dojoflow.schemas.onboarding import OnboardingWebCreate
from dojoflow.services.master import MasterService
from dojoflow.services.onboarding import OnboardingService
from dojoflow.services.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from dojoflow.shared.exceptions import ForbiddenError, UnauthorizedError

PURPOSE_TELEGRAM_LINK = 'telegram_link'
PURPOSE_TELEGRAM_SETUP = 'telegram_setup'
REFRESH_REUSE_GRACE_SECONDS = 30
REFRESH_CHAIN_MAX_HOPS = 20


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
            raise UnauthorizedError('Invalid email or password.')

        if not verify_password(data.password, str(master['password_hash'])):
            raise UnauthorizedError('Invalid email or password.')

        master_id = int(master['id'])
        context = await self.master_service.get_context_by_id(master_id)

        if context is None:
            raise UnauthorizedError('Invalid email or password.')

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

        return await self._start_session_for_master(master_id)

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

    @transactional
    async def _rotate_session(self, session: dict[str, Any]) -> AuthResult:
        result, new_session_id = await self._create_session(
            int(session['master_id'])
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
    async def _start_session_for_master(self, master_id: int) -> AuthResult:
        result, _ = await self._create_session(master_id)

        return result

    async def _start_session(self, context: MasterContextRead) -> AuthResult:
        return await self._start_session_for_master(context.master_id)

    async def _create_session(self, master_id: int) -> tuple[AuthResult, int]:
        context = await self.master_service.get_context_by_id(master_id)

        if context is None:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        refresh_token = generate_refresh_token()
        session_id = await self.refresh_session_repository.create({
            'master_id': master_id,
            'token_hash': hash_refresh_token(refresh_token),
            'expires_at': datetime.now(UTC)
            + timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
        })

        response = AuthTokenResponse(
            access_token=create_access_token(master_id),
            master=MasterContextApiRead.from_context(context),
        )

        return AuthResult(response, refresh_token), session_id

    async def get_me(
        self,
        master_id: int,
    ) -> MasterContextRead:
        context = await self.master_service.get_context_by_id(master_id)

        if context is None:
            raise UnauthorizedError('Master not found.')

        return context

    async def create_telegram_link_token_for_master(
        self,
        master_id: int,
    ) -> TelegramLinkTokenResponse:
        token, expires_at = await self._issue_one_time_token(
            master_id=master_id,
            purpose=PURPOSE_TELEGRAM_LINK,
            ttl_minutes=settings.JWT_TELEGRAM_LINK_TTL_MINUTES,
        )
        deep_link = None

        if settings.TELEGRAM_BOT_USERNAME:
            deep_link = (
                f'https://t.me/{settings.TELEGRAM_BOT_USERNAME}'
                f'?start=link_{token}'
            )

        return TelegramLinkTokenResponse(
            token=token,
            deep_link=deep_link,
            expires_at=expires_at,
        )

    async def create_telegram_setup_token_for_master(
        self,
        master_id: int,
    ) -> TelegramSetupTokenResponse:
        token, expires_at = await self._issue_one_time_token(
            master_id=master_id,
            purpose=PURPOSE_TELEGRAM_SETUP,
            ttl_minutes=settings.JWT_TELEGRAM_SETUP_TTL_MINUTES,
        )

        return TelegramSetupTokenResponse(
            token=token,
            expires_at=expires_at,
        )

    @transactional
    async def set_credentials(
        self,
        data: SetCredentialsRequest,
        *,
        authenticated_master_id: int | None = None,
    ) -> AuthResult:
        if data.setup_token:
            master_id = await self._consume_one_time_token(
                token=data.setup_token,
                purpose=PURPOSE_TELEGRAM_SETUP,
            )
        elif authenticated_master_id is not None:
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
            raise UnauthorizedError(
                'Authentication or setup token is required.'
            )

        context = await self.master_service.set_credentials(
            master_id=master_id,
            email=str(data.email),
            password_hash=hash_password(data.password),
        )

        await self.revoke_all_sessions(master_id)

        return await self._start_session(context)

    @transactional
    async def link_telegram_from_token(
        self,
        token: str,
        telegram_user_id: int,
    ) -> MasterContextRead:
        master_id = await self._consume_one_time_token(
            token=token,
            purpose=PURPOSE_TELEGRAM_LINK,
        )

        return await self.master_service.link_telegram_user(
            master_id=master_id,
            telegram_user_id=telegram_user_id,
        )

    @transactional
    async def _issue_one_time_token(
        self,
        master_id: int,
        purpose: str,
        ttl_minutes: int,
    ) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(16)
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        await self.one_time_token_repository.create({
            'master_id': master_id,
            'token': token,
            'purpose': purpose,
            'expires_at': expires_at,
            'used_at': None,
        })

        return token, expires_at

    @transactional
    async def _consume_one_time_token(
        self,
        token: str,
        purpose: str,
    ) -> int:
        record = await self.one_time_token_repository.get_valid_by_token(
            token=token,
            purpose=purpose,
        )

        if record is None:
            raise UnauthorizedError('Invalid or expired token.')

        await self.one_time_token_repository.update_by_id(
            record_id=int(record['id']),
            data={'used_at': datetime.now(UTC)},
        )

        return int(record['master_id'])
