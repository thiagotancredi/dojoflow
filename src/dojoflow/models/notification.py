from datetime import datetime

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    datetime_column,
    enum_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.models.enums import NotificationStatus, NotificationType


class Notification(BaseModel):
    __tablename__ = 'notification'

    academy_id: Mapped[int] = int_fk('academy.id')

    master_id: Mapped[int | None] = int_fk('master.id', nullable=True)
    student_id: Mapped[int | None] = int_fk('student.id', nullable=True)
    payment_id: Mapped[int | None] = int_fk('payment.id', nullable=True)

    notification_type: Mapped[NotificationType] = enum_column(
        NotificationType,
        default=NotificationType.GENERAL,
    )

    status: Mapped[NotificationStatus] = enum_column(
        NotificationStatus,
        default=NotificationStatus.PENDING,
    )

    message_text: Mapped[str] = str_column(length=4000)

    scheduled_at: Mapped[datetime | None] = datetime_column(nullable=True)
    sent_at: Mapped[datetime | None] = datetime_column(nullable=True)

    error_message: Mapped[str | None] = str_column(
        length=1000,
        nullable=True,
    )
