from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import (
    AuthServiceDep,
    CurrentMasterDep,
    OptionalCurrentMasterDep,
)
from dojoflow.schemas.auth import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    SetCredentialsRequest,
    TelegramLinkTokenResponse,
    TelegramSetupTokenResponse,
)
from dojoflow.schemas.master_context import MasterContextRead

router = APIRouter(prefix='/auth', tags=['Auth'])


@router.post(
    path='/register',
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: AuthRegisterRequest,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    return await auth_service_dep.register(data)


@router.post(
    path='/login',
    status_code=status.HTTP_200_OK,
)
async def login(
    data: AuthLoginRequest,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    return await auth_service_dep.login(data)


@router.post(
    path='/refresh',
    status_code=status.HTTP_200_OK,
)
async def refresh(
    data: AuthRefreshRequest,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    return await auth_service_dep.refresh(data.refresh_token)


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
    auth_service_dep: AuthServiceDep,
    optional_master: OptionalCurrentMasterDep,
) -> AuthTokenResponse:
    authenticated_master_id = (
        optional_master.master_id if optional_master is not None else None
    )

    return await auth_service_dep.set_credentials(
        data,
        authenticated_master_id=authenticated_master_id,
    )
