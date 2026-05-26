from enum import StrEnum


class TelegramFlow(StrEnum):
    ONBOARDING = 'onboarding'


class TelegramStep(StrEnum):
    WAITING_ACADEMY_NAME = 'waiting_academy_name'
    WAITING_MASTER_NAME = 'waiting_master_name'
    COMPLETED = 'completed'
