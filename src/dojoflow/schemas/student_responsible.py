from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import StudentResponsibleRelationship


class StudentResponsibleCreate(BaseModel):
    academy_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    relationship: StudentResponsibleRelationship
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    phone_is_whatsapp: bool = False
    email: str | None = Field(default=None, max_length=255)


class StudentResponsibleRead(ReadBase):
    academy_id: int
    student_id: int
    relationship: StudentResponsibleRelationship
    name: str
    phone: str
    phone_is_whatsapp: bool
    email: str | None
