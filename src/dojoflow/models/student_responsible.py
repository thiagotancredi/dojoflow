from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    enum_column,
    int_fk,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import StudentResponsibleRelationship


class StudentResponsible(BaseModel):
    __tablename__ = 'student_responsible'

    academy_id: Mapped[int] = int_fk('academy.id')
    student_id: Mapped[int] = int_fk('student.id')
    responsible_id: Mapped[int | None] = int_fk(
        'responsible.id',
        nullable=True,
    )

    relationship: Mapped[StudentResponsibleRelationship] = enum_column(
        StudentResponsibleRelationship,
    )
