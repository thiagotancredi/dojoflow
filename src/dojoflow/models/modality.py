from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    bool_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class Modality(BaseModel):
    __tablename__ = 'modality'

    __table_args__ = (
        UniqueConstraint(
            'name',
            name='uq_modality_name',
        ),
    )

    name: Mapped[str] = str_column(length=80)
    emoji: Mapped[str] = str_column(length=10)

    is_active: Mapped[bool] = bool_column(default=True)
