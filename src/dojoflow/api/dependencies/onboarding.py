from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.academy import AcademyServiceDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.master import MasterServiceDep
from dojoflow.services.onboarding import OnboardingService


def _get_onboarding_service(
    academy_service_dep: AcademyServiceDep,
    master_service_dep: MasterServiceDep,
    db_session_dep: DbSessionDep,
) -> OnboardingService:
    return OnboardingService(
        academy_service=academy_service_dep,
        master_service=master_service_dep,
        db_session=db_session_dep,
    )


OnboardingServiceDep = Annotated[
    OnboardingService,
    Depends(_get_onboarding_service),
]
