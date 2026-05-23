from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import ImportRowStatus


class ImportRowCreate(BaseModel):
    academy_id: int = Field(gt=0)
    import_batch_id: int = Field(gt=0)
    row_number: int = Field(gt=0)
    status: ImportRowStatus = ImportRowStatus.PENDING
    raw_data: str | None = Field(default=None, max_length=3000)
    error_message: str | None = Field(default=None, max_length=1000)


class ImportRowRead(ReadBase):
    academy_id: int
    import_batch_id: int
    row_number: int
    status: ImportRowStatus
    raw_data: str | None
    error_message: str | None
