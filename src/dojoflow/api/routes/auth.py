from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from dojoflow.api.dependencies.auth import (
    AuthServiceDep,
    BearerCredentialsDep,
    CurrentMasterDep,
    resolve_optional_master,
)
from dojoflow.api.dependencies.master import MasterServiceDep
from dojoflow.core.settings import settings
from dojoflow.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    SetCredentialsRequest,
    TelegramLinkTokenResponse,
    TelegramSetupTokenResponse,
)
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.shared.exceptions import UnauthorizedError

router = APIRouter(prefix='/auth', tags=['Auth'])

REFRESH_COOKIE_NAME = 'dojoflow_refresh'
REFRESH_COOKIE_PATH = f'{settings.API_V1_PREFIX}/auth'

RefreshCookie = Annotated[
    str | None,
    Cookie(alias=REFRESH_COOKIE_NAME),
]


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TTL_DAYS * 24 * 60 * 60,
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
) -> MasterContextRead:
    return current_master


@router.post(
    path='/telegram/link-token',
    status_code=status.HTTP_200_OK,
)
async def create_telegram_link_token(
    current_master: CurrentMasterDep,
    auth_service_dep: AuthServiceDep,
) -> TelegramLinkTokenResponse:
    return await auth_service_dep.create_telegram_link_token_for_master(
        current_master.master_id
    )


@router.post(
    path='/telegram/setup-token',
    status_code=status.HTTP_200_OK,
)
async def create_telegram_setup_token(
    current_master: CurrentMasterDep,
    auth_service_dep: AuthServiceDep,
) -> TelegramSetupTokenResponse:
    """Issue a short-lived token for Telegram-linked masters.

    Prefer calling this after Telegram ownership is proven (e.g. bot command).
    Authenticated masters can also mint it for themselves.
    """
    return await auth_service_dep.create_telegram_setup_token_for_master(
        current_master.master_id
    )


@router.post(
    path='/set-credentials',
    status_code=status.HTTP_200_OK,
)
async def set_credentials(
    data: SetCredentialsRequest,
    response: Response,
    auth_service_dep: AuthServiceDep,
    master_service_dep: MasterServiceDep,
    credentials: BearerCredentialsDep,
) -> AuthTokenResponse:
    # A supplied setup token takes precedence: the bearer is not even parsed.
    authenticated_master_id = None

    if not data.setup_token:
        optional_master = await resolve_optional_master(
            master_service_dep, credentials
        )
        authenticated_master_id = (
            optional_master.master_id if optional_master is not None else None
        )

    result = await auth_service_dep.set_credentials(
        data,
        authenticated_master_id=authenticated_master_id,
    )
    _set_refresh_cookie(response, result.refresh_token)

    return result.response
