from typing import Any

from sqlalchemy import select

from dojoflow.database.transaction import transactional
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

    @transactional
    async def get_context_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        stmt = (
            select(
                Master.id.label('master_id'),
                Master.name.label('master_name'),
                Master.telegram_user_id,
                Academy.id.label('academy_id'),
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
