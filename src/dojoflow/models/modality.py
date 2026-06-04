from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.base import Base
from dojoflow.database.helper_mapped_columns import (
    bool_column,
    int_pk,
    str_column,
)


class Modality(Base):
    __tablename__ = 'modality'

    __table_args__ = (
        UniqueConstraint(
            'name',
            name='uq_modality_name',
        ),
    )

    id: Mapped[int] = int_pk()

    name: Mapped[str] = str_column(length=80)
    emoji: Mapped[str] = str_column(length=10)

    is_active: Mapped[bool] = bool_column(default=True)
