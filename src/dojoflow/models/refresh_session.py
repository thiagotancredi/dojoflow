from datetime import datetime

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    datetime_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class RefreshSession(BaseModel):
    __tablename__ = 'refresh_session'

    master_id: Mapped[int] = int_fk('master.id')
    token_hash: Mapped[str] = str_column(length=64, unique=True, index=True)
    expires_at: Mapped[datetime] = datetime_column()
    revoked_at: Mapped[datetime | None] = datetime_column(nullable=True)
    replaced_by_id: Mapped[int | None] = int_fk(
        'refresh_session.id',
        nullable=True,
    )
