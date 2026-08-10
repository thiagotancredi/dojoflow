from datetime import UTC, datetime
from typing import Any

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
