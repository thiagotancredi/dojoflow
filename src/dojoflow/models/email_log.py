from datetime import date, datetime

from sqlalchemy import Index
from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    date_column,
    datetime_column,
    enum_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import EmailKind, EmailStatus


class EmailLog(BaseModel):
    """Registro de cada e-mail enviado (ou que falhou)."""

    __tablename__ = 'email_log'

    kind: Mapped[EmailKind] = enum_column(EmailKind)
    status: Mapped[EmailStatus] = enum_column(
        EmailStatus, default=EmailStatus.PENDING
    )
    academy_id: Mapped[int | None] = int_fk('academy.id', nullable=True)
    student_id: Mapped[int | None] = int_fk('student.id', nullable=True)
    master_id: Mapped[int | None] = int_fk('master.id', nullable=True)
    recipient: Mapped[str] = str_column(length=255)
    # 1º dia do mês da cobrança
    reference_month: Mapped[date | None] = date_column(nullable=True)
    provider_message_id: Mapped[str | None] = str_column(
        length=255, nullable=True
    )
    error: Mapped[str | None] = str_column(length=500, nullable=True)
    sent_at: Mapped[datetime | None] = datetime_column(nullable=True)

    __table_args__ = (
        # Um e-mail de cobrança por aluno por mês
        Index(
            'uq_email_log_billing_student_month',
            'student_id',
            'reference_month',
            unique=True,
            postgresql_where="kind = 'billing'",
        ),
    )
