import uuid
from datetime import datetime

from sqlalchemy.orm import Mapped

from dojoflow.database.base import Base
from dojoflow.database.helper_mapped_columns import (
    created_at_column,
    int_pk,
    updated_at_column,
    uuid_public_id,
)


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = int_pk()
    public_id: Mapped[uuid.UUID] = uuid_public_id()

    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
