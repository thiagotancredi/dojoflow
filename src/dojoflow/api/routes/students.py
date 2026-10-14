from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.public_ids import (
    StudentIdDep,
    resolve_modality_id,
    resolve_public_id,
)
from dojoflow.api.dependencies.student import StudentServiceDep
from dojoflow.models.enrollment import Enrollment
from dojoflow.schemas.student import (
    StudentAddressPayload,
    StudentBasicUpdateRequest,
    StudentCreateRequest,
    StudentEnrollmentPayload,
    StudentResponsiblePayload,
)
from dojoflow.schemas.student_api import (
    EnrollmentApiPayload,
    EnrollmentApiUpdateRequest,
    StudentApiRead,
    StudentCreateApiRequest,
    StudentDetailRead,
)

router = APIRouter(prefix='/students', tags=['Students'])


async def _to_internal_enrollment(
    db_session: AsyncSession,
    payload: EnrollmentApiPayload,
) -> StudentEnrollmentPayload:
    modality_id = await resolve_modality_id(db_session, payload.modality_id)

    return StudentEnrollmentPayload(
        modality_id=modality_id,
        **payload.model_dump(exclude={'modality_id'}),
    )


async def _resolve_enrollment_id(
    enrollment_id: UUID,
    student_id: StudentIdDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_public_id(
        db_session_dep,
        Enrollment,
        enrollment_id,
        code='ENROLLMENT_NOT_FOUND',
        extra_filters=[Enrollment.student_id == student_id],
    )


EnrollmentIdDep = Annotated[int, Depends(_resolve_enrollment_id)]


@router.post(
    path='',
    status_code=http_status.HTTP_201_CREATED,
)
async def create_student(
    data: StudentCreateApiRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    db_session_dep: DbSessionDep,
) -> StudentApiRead:
    enrollment = await _to_internal_enrollment(db_session_dep, data.enrollment)
    internal_request = StudentCreateRequest(
        **data.model_dump(exclude={'enrollment'}),
        enrollment=enrollment,
    )

    student = await student_service_dep.create_student(
        academy_id=current_master.academy_id,
        data=internal_request,
    )

    return StudentApiRead.from_record(student.model_dump())


@router.get(
    path='/{student_id}',
    status_code=http_status.HTTP_200_OK,
)
async def get_student_details(
    student_id: StudentIdDep,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> StudentDetailRead:
    details = await student_service_dep.get_details(
        academy_id=current_master.academy_id,
        student_id=student_id,
    )

    return StudentDetailRead.from_details(details)


@router.patch(
    path='/{student_id}',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def update_student_basic_data(
    student_id: StudentIdDep,
    data: StudentBasicUpdateRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    payload = data.model_dump(exclude_unset=True)

    if not payload:
        return

    await student_service_dep.update_basic_data(
        academy_id=current_master.academy_id,
        student_id=student_id,
        data=payload,
    )


@router.put(
    path='/{student_id}/address',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def update_student_address(
    student_id: StudentIdDep,
    data: StudentAddressPayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.update_address(
        academy_id=current_master.academy_id,
        student_id=student_id,
        address_data=data.model_dump(),
    )


@router.delete(
    path='/{student_id}/address',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def remove_student_address(
    student_id: StudentIdDep,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.remove_address(
        academy_id=current_master.academy_id,
        student_id=student_id,
    )


@router.post(
    path='/{student_id}/responsibles',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def add_student_responsible(
    student_id: StudentIdDep,
    data: StudentResponsiblePayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.add_responsible(
        academy_id=current_master.academy_id,
        student_id=student_id,
        responsible_data=data.model_dump(mode='json'),
    )


@router.post(
    path='/{student_id}/enrollments',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def add_student_enrollment(
    student_id: StudentIdDep,
    data: EnrollmentApiPayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    enrollment = await _to_internal_enrollment(db_session_dep, data)

    await student_service_dep.add_enrollment(
        academy_id=current_master.academy_id,
        student_id=student_id,
        data=enrollment,
    )


@router.patch(
    path='/{student_id}/enrollments/{enrollment_id}',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def update_student_enrollment(
    student_id: StudentIdDep,
    enrollment_id: EnrollmentIdDep,
    data: EnrollmentApiUpdateRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    payload = data.model_dump(exclude_unset=True)

    if not payload:
        return

    await student_service_dep.update_enrollment_by_id(
        academy_id=current_master.academy_id,
        student_id=student_id,
        enrollment_id=enrollment_id,
        data=payload,
    )
