from datetime import date

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    date_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class GraduationList(BaseModel):
    __tablename__ = 'graduation_list'

    academy_id: Mapped[int] = int_fk('academy.id')
    modality_id: Mapped[int] = int_fk('modality.id')

    name: Mapped[str] = str_column(length=120)
    exam_date: Mapped[date] = date_column()


class GraduationListEntry(BaseModel):
    """Aluno na lista, com o retrato da faixa no momento em que entrou."""

    __tablename__ = 'graduation_list_entry'

    __table_args__ = (
        UniqueConstraint(
            'graduation_list_id',
            'enrollment_id',
            name='uq_graduation_list_entry_list_enrollment',
        ),
    )

    academy_id: Mapped[int] = int_fk('academy.id')
    graduation_list_id: Mapped[int] = int_fk('graduation_list.id')
    enrollment_id: Mapped[int] = int_fk('enrollment.id')
    target_belt_id: Mapped[int] = int_fk('belt.id')

    snapshot_belt_id: Mapped[int | None] = int_fk('belt.id', nullable=True)
    snapshot_graduated_on: Mapped[date | None] = date_column(nullable=True)
