from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    enum_column,
    int_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.models.enums import ImportRowStatus


class ImportRow(BaseModel):
    __tablename__ = 'import_row'

    __table_args__ = (
        UniqueConstraint(
            'import_batch_id',
            'row_number',
            name='uq_import_row_batch_row_number',
        ),
    )

    academy_id: Mapped[int] = int_fk('academy.id')
    import_batch_id: Mapped[int] = int_fk('import_batch.id')

    row_number: Mapped[int] = int_column()

    status: Mapped[ImportRowStatus] = enum_column(
        ImportRowStatus,
        default=ImportRowStatus.PENDING,
    )

    raw_data: Mapped[str | None] = str_column(
        length=3000,
        nullable=True,
    )

    error_message: Mapped[str | None] = str_column(
        length=1000,
        nullable=True,
    )
