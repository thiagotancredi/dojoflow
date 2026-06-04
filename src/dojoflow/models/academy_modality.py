from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.base import Base
from dojoflow.database.helper_mapped_columns import int_fk, int_pk


class AcademyModality(Base):
    __tablename__ = 'academy_modality'

    __table_args__ = (
        UniqueConstraint(
            'academy_id',
            'modality_id',
            name='uq_academy_modality_academy_id_modality_id',
        ),
    )

    id: Mapped[int] = int_pk()

    academy_id: Mapped[int] = int_fk('academy.id')
    modality_id: Mapped[int] = int_fk('modality.id')
