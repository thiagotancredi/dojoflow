from datetime import date

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import StudentSex


class StudentCreate(BaseModel):
    academy_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    instagram: str | None = Field(default=None, max_length=80)
    birth_date: date | None = None
    sex: StudentSex | None = None


class StudentRead(ReadBase):
    academy_id: int
    name: str
    phone: str | None
    cpf: str | None
    instagram: str | None
    birth_date: date | None
    sex: StudentSex | None
