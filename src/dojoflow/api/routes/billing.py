from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.billing import BillingServiceDep
from dojoflow.api.dependencies.public_ids import StudentIdDep
from dojoflow.schemas.billing_api import StudentBillingApiRead

router = APIRouter(prefix='/students/{student_id}/billing', tags=['Billing'])


@router.get(path='', status_code=status.HTTP_200_OK)
async def read_student_billing(
    student_id: StudentIdDep,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> StudentBillingApiRead:
    billing = await billing_service_dep.student_billing(
        current_master.academy_id, student_id
    )

    return StudentBillingApiRead.from_internal(billing)
