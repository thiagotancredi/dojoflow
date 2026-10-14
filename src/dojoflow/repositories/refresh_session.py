from datetime import datetime
from typing import Any

from sqlalchemy import update

from dojoflow.models.refresh_session import RefreshSession
from dojoflow.repositories.base import BaseRepository


class RefreshSessionRepository(BaseRepository[RefreshSession]):
    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> dict[str, Any] | None:
        return await self.get_one(
            filters=[RefreshSession.token_hash == token_hash],
        )

    async def revoke_all_for_master(
        self,
        master_id: int,
        revoked_at: datetime,
    ) -> None:
        self._ensure_unit_of_work()

        await self.db_session.execute(
            update(RefreshSession)
            .where(
                RefreshSession.master_id == master_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
