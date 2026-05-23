from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.base import Base
from dojoflow.database.helper_mapped_columns import int_fk, int_pk, str_column


class Modality(Base):
    __tablename__ = 'modality'

    __table_args__ = (
        UniqueConstraint(
            'academy_id',
            'name',
            name='uq_modality_academy_id_name',
        ),
    )

    id: Mapped[int] = int_pk()
    academy_id: Mapped[int] = int_fk('academy.id')

    name: Mapped[str] = str_column(length=80)
