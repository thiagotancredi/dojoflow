from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    bool_column,
    enum_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import StudentResponsibleRelationship


class StudentResponsible(BaseModel):
    __tablename__ = 'student_responsible'

    academy_id: Mapped[int] = int_fk('academy.id')
    student_id: Mapped[int] = int_fk('student.id')

    relationship: Mapped[StudentResponsibleRelationship] = enum_column(
        StudentResponsibleRelationship,
    )

    name: Mapped[str] = str_column(length=120)
    phone: Mapped[str] = str_column(length=20)
    phone_is_whatsapp: Mapped[bool] = bool_column(default=False)
    email: Mapped[str | None] = str_column(length=255, nullable=True)
