from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.master import MasterServiceDep
from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.core.settings import settings
from dojoflow.repositories.one_time_token import OneTimeTokenRepository
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.auth import AuthService
from dojoflow.services.security import MASTER_ROLE, get_master_id_from_token
from dojoflow.shared.exceptions import UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)


def _get_one_time_token_repository(
    db_session_dep: DbSessionDep,
) -> OneTimeTokenRepository:
    return OneTimeTokenRepository(db_session=db_session_dep)


OneTimeTokenRepositoryDep = Annotated[
    OneTimeTokenRepository,
    Depends(_get_one_time_token_repository),
]


def _get_auth_service(
    onboarding_service_dep: OnboardingServiceDep,
    master_service_dep: MasterServiceDep,
    one_time_token_repository_dep: OneTimeTokenRepositoryDep,
    db_session_dep: DbSessionDep,
) -> AuthService:
    return AuthService(
        onboarding_service=onboarding_service_dep,
        master_service=master_service_dep,
        one_time_token_repository=one_time_token_repository_dep,
        db_session=db_session_dep,
    )


AuthServiceDep = Annotated[
    AuthService,
    Depends(_get_auth_service),
]


async def _get_current_master(
    master_service_dep: MasterServiceDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> MasterContextRead:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise UnauthorizedError('Authentication required.')

    master_id = get_master_id_from_token(
        credentials.credentials,
        expected_purpose='access',
        expected_role=MASTER_ROLE,
    )
    context = await master_service_dep.get_context_by_id(master_id)

    if context is None:
        raise UnauthorizedError('Master not found.')

    return context


CurrentMasterDep = Annotated[
    MasterContextRead,
    Depends(_get_current_master),
]


async def _get_optional_current_master(
    master_service_dep: MasterServiceDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> MasterContextRead | None:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        return None

    master_id = get_master_id_from_token(
        credentials.credentials,
        expected_purpose='access',
        expected_role=MASTER_ROLE,
    )
    return await master_service_dep.get_context_by_id(master_id)


OptionalCurrentMasterDep = Annotated[
    MasterContextRead | None,
    Depends(_get_optional_current_master),
]


def require_internal_api_key(
    x_internal_api_key: Annotated[
        str | None,
        Header(alias='X-Internal-Api-Key'),
    ] = None,
) -> None:
    if not settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                'Direct onboarding HTTP is disabled. '
                'Use POST /api/v1/auth/register or the Telegram bot.'
            ),
        )

    if x_internal_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid internal API key.',
        )
