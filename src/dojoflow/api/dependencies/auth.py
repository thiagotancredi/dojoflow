from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.master import MasterServiceDep
from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.repositories.one_time_token import OneTimeTokenRepository
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.admin_access import is_admin_email
from dojoflow.services.auth import AuthService, ensure_academy_active
from dojoflow.services.master import MasterService
from dojoflow.services.security import MASTER_ROLE, decode_token
from dojoflow.shared.exceptions import ForbiddenError, UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)


def _get_one_time_token_repository(
    db_session_dep: DbSessionDep,
) -> OneTimeTokenRepository:
    return OneTimeTokenRepository(db_session=db_session_dep)


OneTimeTokenRepositoryDep = Annotated[
    OneTimeTokenRepository,
    Depends(_get_one_time_token_repository),
]


def _get_refresh_session_repository(
    db_session_dep: DbSessionDep,
) -> RefreshSessionRepository:
    return RefreshSessionRepository(db_session=db_session_dep)


RefreshSessionRepositoryDep = Annotated[
    RefreshSessionRepository,
    Depends(_get_refresh_session_repository),
]


def _get_auth_service(
    onboarding_service_dep: OnboardingServiceDep,
    master_service_dep: MasterServiceDep,
    one_time_token_repository_dep: OneTimeTokenRepositoryDep,
    refresh_session_repository_dep: RefreshSessionRepositoryDep,
    db_session_dep: DbSessionDep,
) -> AuthService:
    return AuthService(
        onboarding_service=onboarding_service_dep,
        master_service=master_service_dep,
        one_time_token_repository=one_time_token_repository_dep,
        refresh_session_repository=refresh_session_repository_dep,
        db_session=db_session_dep,
    )


AuthServiceDep = Annotated[
    AuthService,
    Depends(_get_auth_service),
]


async def resolve_master_context(
    master_service: MasterService,
    token: str,
) -> MasterContextRead:
    """Único ponto que transforma o token no contexto (mestre + academia).

    Token de modo suporte (claim acting_academy_id): o administrador vê a
    academia indicada, mesmo desativada, enquanto ainda for administrador.
    """
    payload = decode_token(
        token,
        expected_purpose='access',
        expected_role=MASTER_ROLE,
    )

    try:
        master_id = int(payload['sub'])
        acting_academy_id = payload.get('acting_academy_id')
        acting_academy_id = (
            int(acting_academy_id) if acting_academy_id is not None else None
        )
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError('Invalid token subject.') from exc

    if acting_academy_id is None:
        context = await master_service.get_context_by_id(master_id)

        if context is None:
            raise UnauthorizedError('Master not found.')

        ensure_academy_active(context)

        return context

    context = await master_service.get_support_context(
        master_id, acting_academy_id
    )

    if context is None or not is_admin_email(context.email):
        raise UnauthorizedError(
            'Support session is no longer valid.',
            code='SUPPORT_SESSION_INVALID',
        )

    return context


async def _get_current_master(
    master_service_dep: MasterServiceDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> MasterContextRead:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise UnauthorizedError('Authentication required.')

    return await resolve_master_context(
        master_service_dep, credentials.credentials
    )


CurrentMasterDep = Annotated[
    MasterContextRead,
    Depends(_get_current_master),
]


BearerCredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def _get_current_master_not_in_support(
    current_master: CurrentMasterDep,
) -> MasterContextRead:
    """Ações da conta pessoal: fechadas no modo suporte."""
    if current_master.support_mode:
        raise ForbiddenError(
            'Not available in support mode.', code='SUPPORT_MODE'
        )

    return current_master


AccountMasterDep = Annotated[
    MasterContextRead,
    Depends(_get_current_master_not_in_support),
]
