from uuid import UUID

from fastapi import APIRouter, Query
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.email_billing import EmailBillingServiceDep
from dojoflow.api.dependencies.enrollment_belt import EnrollmentBeltServiceDep
from dojoflow.api.dependencies.public_ids import (
    EnrollmentIdDep,
    StudentIdDep,
    resolve_belt_id,
    resolve_modality_id,
    resolve_public_id,
)
from dojoflow.api.dependencies.student import StudentServiceDep
from dojoflow.database.transaction import unit_of_work
from dojoflow.models.modality import Modality
from dojoflow.models.student_responsible import StudentResponsible
from dojoflow.schemas.enrollment_belt import EnrollmentBeltPayload
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
    StudentListItemRead,
    StudentPageRead,
)
from dojoflow.shared.enums import EnrollmentStatus

router = APIRouter(prefix='/students', tags=['Students'])


async def _to_internal_enrollment(
    db_session: AsyncSession,
    payload: EnrollmentApiPayload,
) -> StudentEnrollmentPayload:
    modality_id = await resolve_modality_id(db_session, payload.modality_id)

    return StudentEnrollmentPayload(
        modality_id=modality_id,
        **payload.model_dump(exclude={'modality_id', 'current_belt'}),
    )


async def _to_internal_current_belt(
    db_session: AsyncSession,
    payload: EnrollmentApiPayload,
    academy_id: int,
) -> EnrollmentBeltPayload | None:
    if payload.current_belt is None:
        return None

    belt_id = await resolve_belt_id(
        db_session, payload.current_belt.belt_id, academy_id
    )

    return EnrollmentBeltPayload(
        belt_id=belt_id,
        graduated_on=payload.current_belt.graduated_on,
    )


@router.get(
    path='',
    status_code=http_status.HTTP_200_OK,
)
async def list_students(  # noqa: PLR0913, PLR0917
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    email_billing_service_dep: EmailBillingServiceDep,
    db_session_dep: DbSessionDep,
    search: str | None = Query(default=None, min_length=1, max_length=120),
    modality_id: UUID | None = None,
    status: EnrollmentStatus | None = None,
    missing_email: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> StudentPageRead:
    internal_modality_id = None

    if modality_id is not None:
        internal_modality_id = await db_session_dep.scalar(
            select(Modality.id).where(Modality.public_id == modality_id)
        )

        if internal_modality_id is None:
            return StudentPageRead(
                items=[], total=0, page=page, page_size=page_size
            )

    students, total = await student_service_dep.list_page(
        current_master.academy_id,
        search=search,
        modality_id=internal_modality_id,
        status=status,
        page=page,
        page_size=page_size,
        student_ids=(
            await email_billing_service_dep.students_without_email_ids(
                current_master.academy_id
            )
            if missing_email
            else None
        ),
    )
    modality_names = await student_service_dep.get_active_modality_names(
        current_master.academy_id,
        [student['id'] for student in students],
    )

    return StudentPageRead(
        items=[
            StudentListItemRead(
                **StudentApiRead.from_record(student).model_dump(),
                modalities=modality_names.get(student['id'], []),
            )
            for student in students
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    path='',
    status_code=http_status.HTTP_201_CREATED,
)
async def create_student(
    data: StudentCreateApiRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
    db_session_dep: DbSessionDep,
) -> StudentApiRead:
    academy_id = current_master.academy_id
    # Resolve tudo antes de gravar (UUID desconhecido → 404 sem tocar no banco)
    enrollments = [
        (
            await _to_internal_enrollment(db_session_dep, item),
            await _to_internal_current_belt(db_session_dep, item, academy_id),
        )
        for item in data.enrollments
    ]
    first_enrollment, _ = enrollments[0]
    internal_request = StudentCreateRequest(
        **data.model_dump(exclude={'enrollments'}),
        enrollment=first_enrollment,
    )

    # Aluno, matrículas e faixas atuais: tudo ou nada
    async with unit_of_work(db_session_dep):
        student = await student_service_dep.create_student(
            academy_id=academy_id,
            data=internal_request,
        )

        for index, (enrollment, current_belt) in enumerate(enrollments):
            if index > 0:
                await student_service_dep.add_enrollment(
                    academy_id=academy_id,
                    student_id=student.id,
                    data=enrollment,
                )

            if current_belt is not None:
                await enrollment_belt_service_dep.add_for_modality(
                    academy_id,
                    student.id,
                    enrollment.modality_id,
                    current_belt,
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
async def add_student_enrollment(  # noqa: PLR0913, PLR0917
    student_id: StudentIdDep,
    data: EnrollmentApiPayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    academy_id = current_master.academy_id
    enrollment = await _to_internal_enrollment(db_session_dep, data)
    current_belt = await _to_internal_current_belt(
        db_session_dep, data, academy_id
    )

    # Matrícula e faixa atual: tudo ou nada
    async with unit_of_work(db_session_dep):
        await student_service_dep.add_enrollment(
            academy_id=academy_id,
            student_id=student_id,
            data=enrollment,
        )

        if current_belt is not None:
            await enrollment_belt_service_dep.add_for_modality(
                academy_id, student_id, enrollment.modality_id, current_belt
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


@router.delete(
    path='/{student_id}/responsibles/{link_id}',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def remove_student_responsible(
    student_id: StudentIdDep,
    link_id: UUID,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    internal_link_id = await resolve_public_id(
        db_session_dep,
        StudentResponsible,
        link_id,
        code='RESPONSIBLE_LINK_NOT_FOUND',
        extra_filters=[StudentResponsible.student_id == student_id],
    )

    await student_service_dep.remove_responsible_link(
        academy_id=current_master.academy_id,
        student_id=student_id,
        student_responsible_id=internal_link_id,
    )
