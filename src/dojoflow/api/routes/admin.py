from typing import Annotated

from fastapi import APIRouter, Query, status

from dojoflow.api.dependencies.admin import (
    AcademyIdDep,
    AdminServiceDep,
    CurrentAdminDep,
)
from dojoflow.api.dependencies.auth import AuthServiceDep
from dojoflow.schemas.admin_api import (
    AdminAcademyCreate,
    AdminAcademyRead,
    AdminAcademyUpdate,
    AdminCredentialsRead,
    AdminPasswordRead,
    AdminStatusUpdate,
)
from dojoflow.schemas.auth import SupportEntryRead
from dojoflow.schemas.master_context import MasterContextApiRead

router = APIRouter(prefix='/admin', tags=['Admin'])


@router.get(path='/me', status_code=status.HTTP_200_OK)
async def admin_me(current_admin: CurrentAdminDep) -> MasterContextApiRead:
    return MasterContextApiRead.from_context(current_admin)


@router.get(path='/academies', status_code=status.HTTP_200_OK)
async def list_academies(
    admin_service_dep: AdminServiceDep,
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> list[AdminAcademyRead]:
    return await admin_service_dep.list_academies(search)


@router.post(path='/academies', status_code=status.HTTP_201_CREATED)
async def create_academy(
    data: AdminAcademyCreate,
    admin_service_dep: AdminServiceDep,
) -> AdminCredentialsRead:
    return await admin_service_dep.create_academy(data)


@router.patch(path='/academies/{academy_id}', status_code=status.HTTP_200_OK)
async def update_academy(
    academy_id: AcademyIdDep,
    data: AdminAcademyUpdate,
    admin_service_dep: AdminServiceDep,
) -> AdminAcademyRead:
    return await admin_service_dep.update_academy(academy_id, data)


@router.post(
    path='/academies/{academy_id}/reset-password',
    status_code=status.HTTP_200_OK,
)
async def reset_password(
    academy_id: AcademyIdDep,
    admin_service_dep: AdminServiceDep,
) -> AdminPasswordRead:
    return await admin_service_dep.reset_password(academy_id)


@router.post(
    path='/academies/{academy_id}/status',
    status_code=status.HTTP_200_OK,
)
async def set_academy_status(
    academy_id: AcademyIdDep,
    data: AdminStatusUpdate,
    admin_service_dep: AdminServiceDep,
) -> AdminAcademyRead:
    return await admin_service_dep.set_status(academy_id, data.status)


@router.post(
    path='/academies/{academy_id}/support-entry',
    status_code=status.HTTP_200_OK,
)
async def create_support_entry(
    academy_id: AcademyIdDep,
    current_admin: CurrentAdminDep,
    auth_service_dep: AuthServiceDep,
) -> SupportEntryRead:
    """Código de uso único (60 s) para entrar na academia em modo suporte."""
    return await auth_service_dep.create_support_entry(
        current_admin.master_id, academy_id
    )
