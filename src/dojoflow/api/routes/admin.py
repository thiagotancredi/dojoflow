from typing import Annotated

from fastapi import APIRouter, Query, status

from dojoflow.api.dependencies.admin import AdminServiceDep, CurrentAdminDep
from dojoflow.schemas.admin_api import (
    AdminAcademyCreate,
    AdminAcademyRead,
    AdminCredentialsRead,
)
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
