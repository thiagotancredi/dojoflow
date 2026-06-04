from enum import StrEnum


class TelegramFlow(StrEnum):
    ONBOARDING = 'onboarding'
    STUDENT_CREATION = 'student_creation'


class TelegramStep(StrEnum):
    WAITING_ACADEMY_NAME = 'waiting_academy_name'
    WAITING_MASTER_NAME = 'waiting_master_name'

    WAITING_STUDENT_NAME = 'waiting_student_name'
    WAITING_STUDENT_MODALITY = 'waiting_student_modality'
    WAITING_STUDENT_SEX = 'waiting_student_sex'
    WAITING_STUDENT_PHONE = 'waiting_student_phone'
    WAITING_STUDENT_IS_WHATSAPP = 'waiting_student_is_whatsapp'
    WAITING_STUDENT_CPF = 'waiting_student_cpf'
    WAITING_STUDENT_INSTAGRAM = 'waiting_student_instagram'
    WAITING_STUDENT_BIRTH_DATE = 'waiting_student_birth_date'
    WAITING_STUDENT_MONTHLY_FEE = 'waiting_student_monthly_fee'
    WAITING_STUDENT_DUE_DAY = 'waiting_student_due_day'
    WAITING_STUDENT_IS_EXEMPT = 'waiting_student_is_exempt'
    WAITING_STUDENT_CONFIRMATION = 'waiting_student_confirmation'

    COMPLETED = 'completed'
