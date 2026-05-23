from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    enum_column,
    int_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.models.enums import ImportStatus


class ImportBatch(BaseModel):
    __tablename__ = 'import_batch'

    academy_id: Mapped[int] = int_fk('academy.id')

    filename: Mapped[str] = str_column(length=255)

    status: Mapped[ImportStatus] = enum_column(
        ImportStatus,
        default=ImportStatus.PENDING,
    )

    total_rows: Mapped[int] = int_column(default=0)
    success_rows: Mapped[int] = int_column(default=0)
    failed_rows: Mapped[int] = int_column(default=0)

    error_message: Mapped[str | None] = str_column(
        length=1000,
        nullable=True,
    )
