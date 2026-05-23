from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import ImportStatus


class ImportBatchCreate(BaseModel):
    academy_id: int = Field(gt=0)
    filename: str = Field(min_length=1, max_length=255)
    status: ImportStatus = ImportStatus.PENDING
    total_rows: int = Field(default=0, ge=0)
    success_rows: int = Field(default=0, ge=0)
    failed_rows: int = Field(default=0, ge=0)
    error_message: str | None = Field(default=None, max_length=1000)


class ImportBatchRead(ReadBase):
    academy_id: int
    filename: str
    status: ImportStatus
    total_rows: int
    success_rows: int
    failed_rows: int
    error_message: str | None
