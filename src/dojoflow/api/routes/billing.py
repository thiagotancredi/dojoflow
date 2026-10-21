from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.billing import BillingServiceDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.public_ids import (
    ChargeIdDep,
    PaymentIdDep,
    StudentIdDep,
    resolve_student_enrollment_id,
)
from dojoflow.schemas.billing_api import (
    AllocationPreviewApiRead,
    ChargeApiRead,
    CreatePaymentApiPayload,
    LaunchChargeApiPayload,
    PaymentApiRead,
    PaymentPreviewApiPayload,
    PaymentPreviewApiRead,
    StudentBillingApiRead,
    UpdateChargeApiPayload,
)
from dojoflow.schemas.billing_settings_api import BillingSettingsApi

router = APIRouter(prefix='/students/{student_id}/billing', tags=['Billing'])
settings_router = APIRouter(
    prefix='/academy/billing-settings', tags=['Billing']
)


@settings_router.get(path='', status_code=status.HTTP_200_OK)
async def read_billing_settings(
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> BillingSettingsApi:
    return await billing_service_dep.get_settings(current_master.academy_id)


@settings_router.put(path='', status_code=status.HTTP_200_OK)
async def save_billing_settings(
    data: BillingSettingsApi,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> BillingSettingsApi:
    return await billing_service_dep.save_settings(
        current_master.academy_id, data
    )


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


@router.post(path='/charges', status_code=status.HTTP_201_CREATED)
async def launch_past_charge(
    student_id: StudentIdDep,
    data: LaunchChargeApiPayload,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
    db_session_dep: DbSessionDep,
) -> ChargeApiRead:
    enrollment_id = await resolve_student_enrollment_id(
        db_session_dep, data.enrollment_id, student_id
    )
    charge = await billing_service_dep.launch_past_charge(
        current_master.academy_id,
        enrollment_id,
        data.reference_month,
        data.amount,
        data.due_date,
    )

    return ChargeApiRead.from_internal(charge)


@router.patch(path='/charges/{charge_id}', status_code=status.HTTP_200_OK)
async def update_charge(
    charge_id: ChargeIdDep,
    data: UpdateChargeApiPayload,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> ChargeApiRead:
    charge = await billing_service_dep.update_charge(
        current_master.academy_id, charge_id, data.amount, data.due_date
    )

    return ChargeApiRead.from_internal(charge)


@router.post(path='/charges/{charge_id}/waive', status_code=status.HTTP_200_OK)
async def waive_charge(
    charge_id: ChargeIdDep,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> ChargeApiRead:
    charge = await billing_service_dep.set_waived(
        current_master.academy_id, charge_id, waived=True
    )

    return ChargeApiRead.from_internal(charge)


@router.delete(
    path='/charges/{charge_id}/waive', status_code=status.HTTP_200_OK
)
async def unwaive_charge(
    charge_id: ChargeIdDep,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> ChargeApiRead:
    charge = await billing_service_dep.set_waived(
        current_master.academy_id, charge_id, waived=False
    )

    return ChargeApiRead.from_internal(charge)


@router.post(path='/payments/preview', status_code=status.HTTP_200_OK)
async def preview_payment(
    student_id: StudentIdDep,
    data: PaymentPreviewApiPayload,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> PaymentPreviewApiRead:
    allocations = await billing_service_dep.preview_payment(
        current_master.academy_id, student_id, data.amount
    )

    return PaymentPreviewApiRead(
        allocations=[
            AllocationPreviewApiRead.from_preview(item) for item in allocations
        ]
    )


@router.post(path='/payments', status_code=status.HTTP_201_CREATED)
async def create_payment(
    student_id: StudentIdDep,
    data: CreatePaymentApiPayload,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> PaymentApiRead:
    payment = await billing_service_dep.create_payment(
        current_master.academy_id,
        student_id,
        data.amount,
        data.paid_on,
        data.method,
        data.notes,
    )

    return PaymentApiRead.from_internal(payment)


@router.delete(
    path='/payments/{payment_id}', status_code=status.HTTP_204_NO_CONTENT
)
async def delete_payment(
    student_id: StudentIdDep,
    payment_id: PaymentIdDep,
    current_master: CurrentMasterDep,
    billing_service_dep: BillingServiceDep,
) -> None:
    await billing_service_dep.delete_payment(
        current_master.academy_id, student_id, payment_id
    )
