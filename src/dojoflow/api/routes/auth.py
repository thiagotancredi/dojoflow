from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from dojoflow.api.dependencies.auth import (
    AccountMasterDep,
    AuthServiceDep,
    CurrentMasterDep,
)
from dojoflow.core.settings import settings
from dojoflow.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    SetCredentialsRequest,
    SupportExchangeRequest,
)
from dojoflow.schemas.master_context import MasterContextApiRead
from dojoflow.services.auth import SUPPORT_SESSION_TTL
from dojoflow.shared.exceptions import UnauthorizedError

router = APIRouter(prefix='/auth', tags=['Auth'])

REFRESH_COOKIE_NAME = 'dojoflow_refresh'
REFRESH_COOKIE_PATH = f'{settings.API_V1_PREFIX}/auth'

RefreshCookie = Annotated[
    str | None,
    Cookie(alias=REFRESH_COOKIE_NAME),
]


def _set_refresh_cookie(
    response: Response,
    refresh_token: str,
    max_age: int = settings.JWT_REFRESH_TTL_DAYS * 24 * 60 * 60,
) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite='lax',
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite='lax',
    )


@router.post(
    path='/register',
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: AuthRegisterRequest,
    response: Response,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    result = await auth_service_dep.register(data)
    _set_refresh_cookie(response, result.refresh_token)

    return result.response


@router.post(
    path='/login',
    status_code=status.HTTP_200_OK,
)
async def login(
    data: AuthLoginRequest,
    response: Response,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    result = await auth_service_dep.login(data)
    _set_refresh_cookie(response, result.refresh_token)

    return result.response


@router.post(
    path='/refresh',
    status_code=status.HTTP_200_OK,
)
async def refresh(
    response: Response,
    auth_service_dep: AuthServiceDep,
    refresh_token: RefreshCookie = None,
) -> AuthTokenResponse:
    if refresh_token is None:
        raise UnauthorizedError(
            'Refresh token is missing.',
            code='REFRESH_TOKEN_INVALID',
        )

    result = await auth_service_dep.refresh(refresh_token)
    _set_refresh_cookie(response, result.refresh_token)

    return result.response


@router.post(
    path='/logout',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    response: Response,
    auth_service_dep: AuthServiceDep,
    refresh_token: RefreshCookie = None,
) -> None:
    await auth_service_dep.logout(refresh_token)
    _clear_refresh_cookie(response)


@router.get(
    path='/me',
    status_code=status.HTTP_200_OK,
)
async def me(
    current_master: CurrentMasterDep,
) -> MasterContextApiRead:
    return MasterContextApiRead.from_context(current_master)


@router.post(
    path='/set-credentials',
    status_code=status.HTTP_200_OK,
)
async def set_credentials(
    data: SetCredentialsRequest,
    response: Response,
    current_master: AccountMasterDep,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    """Troca e-mail e senha de quem está logado (fora do modo suporte)."""
    result = await auth_service_dep.set_credentials(
        data,
        authenticated_master_id=current_master.master_id,
    )
    _set_refresh_cookie(response, result.refresh_token)

    return result.response


@router.post(
    path='/support/exchange',
    status_code=status.HTTP_200_OK,
)
async def exchange_support_code(
    data: SupportExchangeRequest,
    response: Response,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    """Troca o código de uso único do painel por uma sessão de suporte."""
    result = await auth_service_dep.exchange_support_code(data.code)
    _set_refresh_cookie(
        response,
        result.refresh_token,
        max_age=int(SUPPORT_SESSION_TTL.total_seconds()),
    )

    return result.response
