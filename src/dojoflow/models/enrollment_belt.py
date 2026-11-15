from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import date_column, int_fk
from dojoflow.models.base_model import BaseModel


class EnrollmentBelt(BaseModel):
    """Histórico de faixas de uma matrícula (aluno × modalidade)."""

    __tablename__ = 'enrollment_belt'

    academy_id: Mapped[int] = int_fk('academy.id')
    enrollment_id: Mapped[int] = int_fk('enrollment.id')
    belt_id: Mapped[int] = int_fk('belt.id')

    graduated_on: Mapped[date] = date_column()

    # Faixa gravada pela aprovação num exame: desfazer apaga só estas
    graduation_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey('graduation_list_entry.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
