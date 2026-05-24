from fastapi import APIRouter, status

from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.schemas.master import (
    MasterRegistrationCreate,
    MasterRegistrationRead,
)

router = APIRouter(prefix='/onboarding', tags=['Onboarding'])


@router.post(
    path='/master',
    status_code=status.HTTP_201_CREATED,
)
async def register_master(
    data: MasterRegistrationCreate,
    onboarding_service_dep: OnboardingServiceDep,
) -> MasterRegistrationRead:
    return await onboarding_service_dep.register_master(data)
