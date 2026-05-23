from typing import Any

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import AuditAction


class AuditLogCreate(BaseModel):
    academy_id: int | None = Field(default=None, gt=0)
    master_id: int | None = Field(default=None, gt=0)
    action: AuditAction
    entity_name: str = Field(min_length=1, max_length=120)
    entity_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=1000)
    old_data: dict[str, Any] | None = None
    new_data: dict[str, Any] | None = None


class AuditLogRead(ReadBase):
    academy_id: int | None
    master_id: int | None
    action: AuditAction
    entity_name: str
    entity_id: int | None
    description: str | None
    old_data: dict[str, Any] | None
    new_data: dict[str, Any] | None
