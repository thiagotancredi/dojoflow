from datetime import datetime

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    datetime_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class OneTimeToken(BaseModel):
    __tablename__ = 'one_time_token'

    master_id: Mapped[int] = int_fk('master.id')
    token: Mapped[str] = str_column(length=64, unique=True, index=True)
    purpose: Mapped[str] = str_column(length=40)
    expires_at: Mapped[datetime] = datetime_column()
    used_at: Mapped[datetime | None] = datetime_column(nullable=True)
