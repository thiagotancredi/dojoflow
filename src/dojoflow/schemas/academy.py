from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import AcademyStatus


class AcademyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class AcademyRead(ReadBase):
    name: str
    status: AcademyStatus
