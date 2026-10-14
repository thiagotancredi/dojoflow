from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.models.base_model import BaseModel
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
