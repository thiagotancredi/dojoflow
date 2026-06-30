from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import StudentResponsibleRelationship


class StudentResponsibleCreate(BaseModel):
    academy_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    responsible_id: int = Field(gt=0)
    relationship: StudentResponsibleRelationship


class StudentResponsibleRead(ReadBase):
    academy_id: int
    student_id: int
    responsible_id: int
    relationship: StudentResponsibleRelationship
