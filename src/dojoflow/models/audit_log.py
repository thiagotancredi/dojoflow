from typing import Any

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    enum_column,
    int_column,
    int_fk,
    json_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.models.enums import AuditAction


class AuditLog(BaseModel):
    __tablename__ = 'audit_log'

    academy_id: Mapped[int | None] = int_fk('academy.id', nullable=True)
    master_id: Mapped[int | None] = int_fk('master.id', nullable=True)

    action: Mapped[AuditAction] = enum_column(AuditAction)

    entity_name: Mapped[str] = str_column(length=120)
    entity_id: Mapped[int | None] = int_column(nullable=True)

    description: Mapped[str | None] = str_column(
        length=1000,
        nullable=True,
    )

    old_data: Mapped[dict[str, Any] | None] = json_column(nullable=True)
    new_data: Mapped[dict[str, Any] | None] = json_column(nullable=True)
