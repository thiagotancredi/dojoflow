from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.email_billing import EmailBillingServiceDep
from dojoflow.schemas.email_billing_api import (
    EmailBillingStatusApi,
    EmailBillingUpdateApi,
    EmailPreviewApi,
)

router = APIRouter(prefix='/academy/email-billing', tags=['Billing'])


@router.get(path='', status_code=status.HTTP_200_OK)
async def read_email_billing(
    current_master: CurrentMasterDep,
    email_billing_service_dep: EmailBillingServiceDep,
) -> EmailBillingStatusApi:
    return await email_billing_service_dep.status(current_master.academy_id)


@router.put(path='', status_code=status.HTTP_200_OK)
async def update_email_billing(
    data: EmailBillingUpdateApi,
    current_master: CurrentMasterDep,
    email_billing_service_dep: EmailBillingServiceDep,
) -> EmailBillingStatusApi:
    """Liga ou desliga a cobrança por e-mail."""
    return await email_billing_service_dep.set_enabled(
        current_master.academy_id, data.enabled
    )


@router.get(path='/preview', status_code=status.HTTP_200_OK)
async def preview_email_billing(
    current_master: CurrentMasterDep,
    email_billing_service_dep: EmailBillingServiceDep,
) -> EmailPreviewApi:
    return await email_billing_service_dep.preview(current_master.academy_id)
