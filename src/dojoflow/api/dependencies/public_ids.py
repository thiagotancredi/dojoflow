from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.base_model import BaseModel
from dojoflow.models.belt import Belt
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.graduation_list import GraduationList
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.shared.exceptions import NotFoundError


async def resolve_public_id(
    db_session: AsyncSession,
    model: type[BaseModel],
    public_id: UUID,
    *,
    code: str,
    extra_filters: list[ColumnElement[bool]] | None = None,
) -> int:
    stmt = select(model.id).where(model.public_id == public_id)

    for condition in extra_filters or []:
        stmt = stmt.where(condition)

    internal_id = await db_session.scalar(stmt)

    if internal_id is None:
        raise NotFoundError(
            f'Could not find {model.__name__}.',
            code=code,
        )

    return internal_id


async def resolve_modality_id(
    db_session: AsyncSession,
    public_id: UUID,
) -> int:
    return await resolve_public_id(
        db_session,
        Modality,
        public_id,
        code='MODALITY_NOT_FOUND',
    )


async def _resolve_student_id(
    student_id: UUID,
    current_master: CurrentMasterDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_public_id(
        db_session_dep,
        Student,
        student_id,
        code='STUDENT_NOT_FOUND',
        extra_filters=[Student.academy_id == current_master.academy_id],
    )


StudentIdDep = Annotated[int, Depends(_resolve_student_id)]


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


async def _resolve_belt_record_id(
    record_id: UUID,
    enrollment_id: EnrollmentIdDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_public_id(
        db_session_dep,
        EnrollmentBelt,
        record_id,
        code='BELT_RECORD_NOT_FOUND',
        extra_filters=[EnrollmentBelt.enrollment_id == enrollment_id],
    )


BeltRecordIdDep = Annotated[int, Depends(_resolve_belt_record_id)]


async def _resolve_enabled_modality_id(
    modality_id: UUID,
    current_master: CurrentMasterDep,
    db_session_dep: DbSessionDep,
) -> int:
    internal_id = await resolve_modality_id(db_session_dep, modality_id)
    enabled = await db_session_dep.scalar(
        select(AcademyModality.id).where(
            AcademyModality.academy_id == current_master.academy_id,
            AcademyModality.modality_id == internal_id,
        )
    )

    if enabled is None:
        raise NotFoundError(
            'This modality is not configured for this academy.',
            code='MODALITY_NOT_ENABLED',
        )

    return internal_id


EnabledModalityIdDep = Annotated[int, Depends(_resolve_enabled_modality_id)]


async def resolve_belt_id(
    db_session: AsyncSession,
    public_id: UUID,
    academy_id: int,
) -> int:
    return await resolve_public_id(
        db_session,
        Belt,
        public_id,
        code='BELT_NOT_FOUND',
        extra_filters=[Belt.academy_id == academy_id],
    )


async def _resolve_belt_id(
    belt_id: UUID,
    current_master: CurrentMasterDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_belt_id(
        db_session_dep, belt_id, current_master.academy_id
    )


BeltIdDep = Annotated[int, Depends(_resolve_belt_id)]


async def _resolve_graduation_list_id(
    list_id: UUID,
    current_master: CurrentMasterDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_public_id(
        db_session_dep,
        GraduationList,
        list_id,
        code='GRADUATION_LIST_NOT_FOUND',
        extra_filters=[GraduationList.academy_id == current_master.academy_id],
    )


GraduationListIdDep = Annotated[int, Depends(_resolve_graduation_list_id)]
