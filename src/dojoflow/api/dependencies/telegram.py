from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.master import MasterServiceDep
from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.api.dependencies.telegram_conversation_state import (
    TelegramConversationStateServiceDep,
)
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.services.telegram_webhook import TelegramWebhookService


def get_telegram_service() -> TelegramService:
    return TelegramService()


TelegramServiceDep = Annotated[
    TelegramService,
    Depends(get_telegram_service),
]


def get_telegram_webhook_service(
    telegram_service_dep: TelegramServiceDep,
    master_service_dep: MasterServiceDep,
    onboarding_service_dep: OnboardingServiceDep,
    telegram_conversation_state_service_dep: (
        TelegramConversationStateServiceDep
    ),
) -> TelegramWebhookService:
    return TelegramWebhookService(
        telegram_service=telegram_service_dep,
        master_service=master_service_dep,
        onboarding_service=onboarding_service_dep,
        telegram_conversation_state_service=(
            telegram_conversation_state_service_dep
        ),
    )


TelegramWebhookServiceDep = Annotated[
    TelegramWebhookService,
    Depends(get_telegram_webhook_service),
]
