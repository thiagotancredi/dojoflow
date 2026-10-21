from typing import Any

from sqlalchemy import select

from dojoflow.models.academy import Academy
from dojoflow.models.master import Master
from dojoflow.repositories.base import BaseRepository


class MasterRepository(BaseRepository[Master]):
    async def get_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        return await self.get_one(
            filters=[Master.telegram_user_id == telegram_user_id],
        )

    async def get_by_email(
        self,
        email: str,
    ) -> dict[str, Any] | None:
        return await self.get_one(
            filters=[Master.email == email],
        )

    async def get_context_by_id(
        self,
        master_id: int,
        academy_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Mestre + academia. Com academy_id, usa essa academia no lugar
        da academia do mestre (modo suporte)."""
        stmt = (
            select(
                Master.id.label('master_id'),
                Master.public_id.label('master_public_id'),
                Master.name.label('master_name'),
                Master.telegram_user_id,
                Master.email,
                Master.phone,
                Academy.id.label('academy_id'),
                Academy.public_id.label('academy_public_id'),
                Academy.name.label('academy_name'),
                Academy.status.label('academy_status'),
            )
            .join(
                Academy,
                Academy.id
                == (
                    academy_id if academy_id is not None else Master.academy_id
                ),
            )
            .where(Master.id == master_id)
        )

        result = await self.db_session.execute(stmt)
        record = result.mappings().one_or_none()

        if record is None:
            return None

        return dict(record)

    async def get_context_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        stmt = (
            select(
                Master.id.label('master_id'),
                Master.public_id.label('master_public_id'),
                Master.name.label('master_name'),
                Master.telegram_user_id,
                Master.email,
                Master.phone,
                Academy.id.label('academy_id'),
                Academy.public_id.label('academy_public_id'),
                Academy.name.label('academy_name'),
                Academy.status.label('academy_status'),
            )
            .join(Academy, Academy.id == Master.academy_id)
            .where(Master.telegram_user_id == telegram_user_id)
        )

        result = await self.db_session.execute(stmt)
        record = result.mappings().one_or_none()

        if record is None:
            return None

        return dict(record)
