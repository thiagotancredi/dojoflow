from fastapi import APIRouter, status

from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.schemas.onboarding import OnboardingCreate, OnboardingRead

router = APIRouter(prefix='/onboarding', tags=['Onboarding'])


@router.post(
    path='',
    status_code=status.HTTP_201_CREATED,
)
async def register_onboarding(
    data: OnboardingCreate,
    onboarding_service_dep: OnboardingServiceDep,
) -> OnboardingRead:
    return await onboarding_service_dep.register_onboarding(data)
