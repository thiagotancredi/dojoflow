from typing import Annotated
from uuid import UUID

from fastapi import Depends

from dojoflow.api.dependencies.academy import AcademyRepositoryDep
from dojoflow.api.dependencies.auth import (
    CurrentMasterDep,
    RefreshSessionRepositoryDep,
)
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.master import MasterRepositoryDep
from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.api.dependencies.public_ids import resolve_public_id
from dojoflow.core.settings import settings
from dojoflow.models.academy import Academy
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.admin import AdminService
from dojoflow.shared.exceptions import ForbiddenError


def is_admin(context: MasterContextRead) -> bool:
    admin_email = settings.ADMIN_EMAIL.strip().lower()

    return bool(admin_email) and (context.email or '') == admin_email


def _get_current_admin(current_master: CurrentMasterDep) -> MasterContextRead:
    if not is_admin(current_master):
        raise ForbiddenError('Admin only.', code='ADMIN_ONLY')

    return current_master


CurrentAdminDep = Annotated[MasterContextRead, Depends(_get_current_admin)]


def _get_admin_service(  # noqa: PLR0913, PLR0917
    current_admin: CurrentAdminDep,
    academy_repository_dep: AcademyRepositoryDep,
    onboarding_service_dep: OnboardingServiceDep,
    master_repository_dep: MasterRepositoryDep,
    refresh_session_repository_dep: RefreshSessionRepositoryDep,
    db_session_dep: DbSessionDep,
) -> AdminService:
    return AdminService(
        academy_repository=academy_repository_dep,
        onboarding_service=onboarding_service_dep,
        master_repository=master_repository_dep,
        refresh_session_repository=refresh_session_repository_dep,
        db_session=db_session_dep,
        own_academy_id=current_admin.academy_id,
    )


AdminServiceDep = Annotated[AdminService, Depends(_get_admin_service)]


async def _get_academy_id(
    academy_id: UUID,
    # Checa o administrador antes de procurar a academia (não revela se
    # um id existe para quem não é administrador)
    _current_admin: CurrentAdminDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_public_id(
        db_session_dep, Academy, academy_id, code='ACADEMY_NOT_FOUND'
    )


AcademyIdDep = Annotated[int, Depends(_get_academy_id)]
