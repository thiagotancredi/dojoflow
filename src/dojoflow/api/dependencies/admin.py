from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.academy import AcademyRepositoryDep
from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.core.settings import settings
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


def _get_admin_service(
    current_admin: CurrentAdminDep,
    academy_repository_dep: AcademyRepositoryDep,
    onboarding_service_dep: OnboardingServiceDep,
    db_session_dep: DbSessionDep,
) -> AdminService:
    return AdminService(
        academy_repository=academy_repository_dep,
        onboarding_service=onboarding_service_dep,
        db_session=db_session_dep,
        own_academy_id=current_admin.academy_id,
    )


AdminServiceDep = Annotated[AdminService, Depends(_get_admin_service)]
