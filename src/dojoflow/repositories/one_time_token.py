from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update

from dojoflow.models.one_time_token import OneTimeToken
from dojoflow.repositories.base import BaseRepository


class OneTimeTokenRepository(BaseRepository[OneTimeToken]):
    async def get_valid_by_token(
        self,
        token: str,
        purpose: str,
    ) -> dict[str, Any] | None:
        record = await self.get_one(
            filters=[
                OneTimeToken.token == token,
                OneTimeToken.purpose == purpose,
                OneTimeToken.used_at.is_(None),
                OneTimeToken.expires_at > datetime.now(UTC),
            ],
        )

        return record

    async def invalidate_open(self, master_id: int, purpose: str) -> None:
        """Marca como usados os códigos ainda válidos da conta."""
        self._ensure_unit_of_work()

        await self.db_session.execute(
            update(OneTimeToken)
            .where(
                OneTimeToken.master_id == master_id,
                OneTimeToken.purpose == purpose,
                OneTimeToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )

    async def count_created_since(
        self, master_id: int, purpose: str, since: datetime
    ) -> int:
        return await self.count(
            filters=[
                OneTimeToken.master_id == master_id,
                OneTimeToken.purpose == purpose,
                OneTimeToken.created_at >= since,
            ]
        )

    async def consume_valid(self, token: str, purpose: str) -> int | None:
        """Gasta o código de uma vez só e devolve o id da conta.

        O UPDATE condicional trava a linha: dois pedidos ao mesmo tempo
        não passam os dois.
        """
        self._ensure_unit_of_work()
        now = datetime.now(UTC)

        return await self.db_session.scalar(
            update(OneTimeToken)
            .where(
                OneTimeToken.token == token,
                OneTimeToken.purpose == purpose,
                OneTimeToken.used_at.is_(None),
                OneTimeToken.expires_at > now,
            )
            .values(used_at=now)
            .returning(OneTimeToken.master_id)
        )
