from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.enrollment_belt import EnrollmentBeltServiceDep
from dojoflow.api.dependencies.public_ids import (
    BeltRecordIdDep,
    EnrollmentIdDep,
    resolve_belt_id,
)
from dojoflow.schemas.enrollment_belt import EnrollmentBeltPayload
from dojoflow.schemas.enrollment_belt_api import (
    BeltRecordApiRead,
    EnrollmentBeltApiPayload,
    EnrollmentBeltsApiRead,
)
from dojoflow.services.belt_rules import (
    eligible_on,
    evaluate_eligibility,
    local_today,
)

router = APIRouter(
    prefix='/students/{student_id}/enrollments/{enrollment_id}/belts',
    tags=['Belts'],
)


async def _to_internal(
    data: EnrollmentBeltApiPayload,
    academy_id: int,
    db_session: DbSessionDep,
) -> EnrollmentBeltPayload:
    belt_id = await resolve_belt_id(db_session, data.belt_id, academy_id)

    return EnrollmentBeltPayload(
        belt_id=belt_id, graduated_on=data.graduated_on
    )


@router.get(path='', status_code=status.HTTP_200_OK)
async def read_enrollment_belts(
    enrollment_id: EnrollmentIdDep,
    current_master: CurrentMasterDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
) -> EnrollmentBeltsApiRead:
    history = await enrollment_belt_service_dep.list_history(
        current_master.academy_id, enrollment_id
    )
    current = history[0] if history else None
    graduated_on = current.graduated_on if current else None
    amount = current.belt.min_time_amount if current else None
    unit = current.belt.min_time_unit if current else None

    return EnrollmentBeltsApiRead(
        current=BeltRecordApiRead.from_internal(current) if current else None,
        eligibility=evaluate_eligibility(
            graduated_on, amount, unit, local_today()
        ),
        eligible_on=(
            eligible_on(graduated_on, amount, unit) if graduated_on else None
        ),
        history=[BeltRecordApiRead.from_internal(item) for item in history],
    )


@router.post(path='', status_code=status.HTTP_204_NO_CONTENT)
async def register_enrollment_belt(
    enrollment_id: EnrollmentIdDep,
    data: EnrollmentBeltApiPayload,
    current_master: CurrentMasterDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    payload = await _to_internal(
        data, current_master.academy_id, db_session_dep
    )

    await enrollment_belt_service_dep.add(
        current_master.academy_id, enrollment_id, payload
    )


@router.put(path='/{record_id}', status_code=status.HTTP_204_NO_CONTENT)
async def update_enrollment_belt(  # noqa: PLR0913, PLR0917
    enrollment_id: EnrollmentIdDep,
    record_id: BeltRecordIdDep,
    data: EnrollmentBeltApiPayload,
    current_master: CurrentMasterDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    payload = await _to_internal(
        data, current_master.academy_id, db_session_dep
    )

    await enrollment_belt_service_dep.update(
        current_master.academy_id, enrollment_id, record_id, payload
    )


@router.delete(path='/{record_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment_belt(
    enrollment_id: EnrollmentIdDep,
    record_id: BeltRecordIdDep,
    current_master: CurrentMasterDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
) -> None:
    await enrollment_belt_service_dep.delete(
        current_master.academy_id, enrollment_id, record_id
    )
