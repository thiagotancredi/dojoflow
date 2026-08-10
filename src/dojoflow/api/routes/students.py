from typing import Any

from fastapi import APIRouter, Query, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.student import StudentServiceDep
from dojoflow.schemas.student import (
    StudentAddressPayload,
    StudentBasicUpdateRequest,
    StudentCreateRequest,
    StudentEnrollmentUpdateRequest,
    StudentModalityUpdateRequest,
    StudentRead,
    StudentResponsiblePayload,
)

router = APIRouter(prefix='/students', tags=['Students'])


@router.get(
    path='',
    status_code=status.HTTP_200_OK,
)
async def list_students(
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    search: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[StudentRead]:
    if search:
        return await student_service_dep.search_by_name(
            academy_id=current_master.academy_id,
            search_text=search,
            limit=limit,
        )

    return await student_service_dep.list_by_academy(
        academy_id=current_master.academy_id,
        limit=limit,
    )


@router.get(
    path='/{student_id}',
    status_code=status.HTTP_200_OK,
)
async def get_student_details(
    student_id: int,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> dict[str, Any]:
    return await student_service_dep.get_details(
        academy_id=current_master.academy_id,
        student_id=student_id,
    )


@router.post(
    path='',
    status_code=status.HTTP_201_CREATED,
)
async def create_student(
    data: StudentCreateRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> StudentRead:
    return await student_service_dep.create_student(
        academy_id=current_master.academy_id,
        data=data,
    )


@router.patch(
    path='/{student_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_student_basic_data(
    student_id: int,
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


@router.patch(
    path='/{student_id}/modality',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_student_modality(
    student_id: int,
    data: StudentModalityUpdateRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.update_modality(
        academy_id=current_master.academy_id,
        student_id=student_id,
        modality_id=data.modality_id,
    )


@router.patch(
    path='/{student_id}/enrollment',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_student_enrollment(
    student_id: int,
    data: StudentEnrollmentUpdateRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    payload = data.model_dump(exclude_unset=True)

    if not payload:
        return

    await student_service_dep.update_enrollment(
        academy_id=current_master.academy_id,
        student_id=student_id,
        data=payload,
    )


@router.put(
    path='/{student_id}/address',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_student_address(
    student_id: int,
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
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_student_address(
    student_id: int,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.remove_address(
        academy_id=current_master.academy_id,
        student_id=student_id,
    )


@router.post(
    path='/{student_id}/responsibles',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_student_responsible(
    student_id: int,
    data: StudentResponsiblePayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.add_responsible(
        academy_id=current_master.academy_id,
        student_id=student_id,
        responsible_data=data.model_dump(mode='json'),
    )
