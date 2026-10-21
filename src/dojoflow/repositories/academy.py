from typing import Any

from sqlalchemy import Select, func, or_, select

from dojoflow.models.academy import Academy
from dojoflow.models.master import Master
from dojoflow.repositories.base import BaseRepository


def _with_master_stmt() -> Select[Any]:
    # Um mestre por academia na V1: o primeiro criado
    first_master_id = (
        select(func.min(Master.id))
        .where(Master.academy_id == Academy.id)
        .correlate(Academy)
        .scalar_subquery()
    )

    return select(
        Academy.id.label('academy_id'),
        Academy.public_id.label('academy_public_id'),
        Academy.name.label('academy_name'),
        Academy.status.label('academy_status'),
        Academy.created_at.label('academy_created_at'),
        Master.id.label('master_id'),
        Master.public_id.label('master_public_id'),
        Master.name.label('master_name'),
        Master.email.label('master_email'),
        Master.phone.label('master_phone'),
    ).outerjoin(Master, Master.id == first_master_id)


class AcademyRepository(BaseRepository[Academy]):
    async def list_with_master(
        self,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        stmt = _with_master_stmt().order_by(
            Academy.created_at.desc(), Academy.id.desc()
        )

        if search and search.strip():
            pattern = f'%{search.strip()}%'
            stmt = stmt.where(
                or_(Academy.name.ilike(pattern), Master.name.ilike(pattern))
            )

        result = await self.db_session.execute(stmt)

        return [dict(row) for row in result.mappings().all()]

    async def get_with_master(
        self,
        academy_id: int,
    ) -> dict[str, Any] | None:
        stmt = _with_master_stmt().where(Academy.id == academy_id)
        result = await self.db_session.execute(stmt)
        record = result.mappings().one_or_none()

        return dict(record) if record is not None else None
