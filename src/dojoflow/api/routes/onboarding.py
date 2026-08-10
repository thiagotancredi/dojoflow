
from fastapi import APIRouter, Depends, status

from dojoflow.api.dependencies.auth import require_internal_api_key
from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.schemas.onboarding import OnboardingCreate, OnboardingRead

router = APIRouter(prefix='/onboarding', tags=['Onboarding'])


@router.post(
    path='',
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_internal_api_key)],
    deprecated=True,
)
async def register_onboarding(
    data: OnboardingCreate,
    onboarding_service_dep: OnboardingServiceDep,
) -> OnboardingRead:
    """Deprecated Telegram-style HTTP onboarding.

    Prefer the Telegram bot or POST /api/v1/auth/register.
    Requires X-Internal-Api-Key when INTERNAL_API_KEY is configured.
    """
    return await onboarding_service_dep.register_onboarding(data)
