from datetime import datetime

from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase
from dojoflow.shared.enums import NotificationStatus, NotificationType


class NotificationCreate(BaseModel):
    academy_id: int = Field(gt=0)
    master_id: int | None = Field(default=None, gt=0)
    student_id: int | None = Field(default=None, gt=0)
    payment_id: int | None = Field(default=None, gt=0)
    notification_type: NotificationType = NotificationType.GENERAL
    status: NotificationStatus = NotificationStatus.PENDING
    message_text: str = Field(min_length=1, max_length=4000)
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    error_message: str | None = Field(default=None, max_length=1000)


class NotificationRead(ReadBase):
    academy_id: int
    master_id: int | None
    student_id: int | None
    payment_id: int | None
    notification_type: NotificationType
    status: NotificationStatus
    message_text: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    error_message: str | None
