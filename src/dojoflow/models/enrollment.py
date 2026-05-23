from decimal import Decimal

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    bool_column,
    enum_column,
    int_column,
    int_fk,
    money_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import EnrollmentStatus


class Enrollment(BaseModel):
    __tablename__ = 'enrollment'

    __table_args__ = (
        UniqueConstraint(
            'academy_id',
            'student_id',
            'modality_id',
            name='uq_enrollment_academy_student_modality',
        ),
    )

    academy_id: Mapped[int] = int_fk('academy.id')
    student_id: Mapped[int] = int_fk('student.id')
    modality_id: Mapped[int] = int_fk('modality.id')

    status: Mapped[EnrollmentStatus] = enum_column(
        EnrollmentStatus,
        default=EnrollmentStatus.ACTIVE,
    )

    monthly_fee: Mapped[Decimal | None] = money_column(nullable=True)
    due_day: Mapped[int | None] = int_column(nullable=True)

    is_exempt: Mapped[bool] = bool_column(default=False)
