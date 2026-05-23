import enum


class AcademyStatus(str, enum.Enum):
    ACTIVE = 'active'
    BLOCKED = 'blocked'


class StudentSex(str, enum.Enum):
    MALE = 'male'
    FEMALE = 'female'


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class PaymentMethod(str, enum.Enum):
    CASH = 'cash'
    PIX = 'pix'
    CREDIT_CARD = 'credit_card'
    DEBIT_CARD = 'debit_card'
    BANK_TRANSFER = 'bank_transfer'
    OTHER = 'other'


class PaymentStatus(str, enum.Enum):
    PENDING = 'pending'
    PARTIAL = 'partial'
    PAID = 'paid'
    OVERDUE = 'overdue'
    WAIVED = 'waived'
    PENDING_CONFIGURATION = 'pending_configuration'


class ImportStatus(str, enum.Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    DONE = 'done'
    FAILED = 'failed'


class ImportRowStatus(str, enum.Enum):
    PENDING = 'pending'
    IMPORTED = 'imported'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class TelegramMessageDirection(str, enum.Enum):
    INBOUND = 'inbound'
    OUTBOUND = 'outbound'


class TelegramMessageStatus(str, enum.Enum):
    RECEIVED = 'received'
    SENT = 'sent'
    FAILED = 'failed'


class NotificationType(str, enum.Enum):
    PAYMENT_DUE_SOON = 'payment_due_soon'
    PAYMENT_OVERDUE = 'payment_overdue'
    MONTHLY_SUMMARY = 'monthly_summary'
    GENERAL = 'general'


class NotificationStatus(str, enum.Enum):
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    CANCELED = 'canceled'


class AuditAction(str, enum.Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    IMPORT = 'import'
    PAYMENT_REGISTERED = 'payment_registered'
    PAYMENT_ALLOCATED = 'payment_allocated'
    NOTIFICATION_SENT = 'notification_sent'
    STATUS_CHANGED = 'status_changed'
