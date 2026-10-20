from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import (
    enum_column,
    int_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import DurationUnit

DEFAULT_MARKS_COLOR = '#d4a017'


class Belt(BaseModel):
    __tablename__ = 'belt'

    __table_args__ = (
        UniqueConstraint(
            'academy_id',
            'modality_id',
            'name',
            name='uq_belt_academy_modality_name',
        ),
    )

    academy_id: Mapped[int] = int_fk('academy.id')
    modality_id: Mapped[int] = int_fk('modality.id')

    name: Mapped[str] = str_column(length=80)

    primary_color: Mapped[str] = str_column(length=7)
    stripe_color: Mapped[str | None] = str_column(length=7, nullable=True)
    marks: Mapped[int] = int_column(default=0)
    marks_color: Mapped[str] = mapped_column(
        String(7),
        default=DEFAULT_MARKS_COLOR,
        nullable=False,
    )
    tip_color: Mapped[str | None] = str_column(length=7, nullable=True)

    min_time_amount: Mapped[int | None] = int_column(nullable=True)
    min_time_unit: Mapped[DurationUnit | None] = enum_column(
        DurationUnit,
        nullable=True,
    )

    position: Mapped[int] = int_column()
