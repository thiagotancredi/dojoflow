from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.master import MasterServiceDep
from dojoflow.api.dependencies.modality import ModalityServiceDep
from dojoflow.api.dependencies.onboarding import OnboardingServiceDep
from dojoflow.api.dependencies.student import StudentServiceDep
from dojoflow.api.dependencies.telegram_conversation_state import (
    TelegramConversationStateServiceDep,
)
from dojoflow.integrations.cep.client import CepClient
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.services.cep import CepService
from dojoflow.services.telegram_webhook import TelegramWebhookService


def get_telegram_service() -> TelegramService:
    return TelegramService()


TelegramServiceDep = Annotated[
    TelegramService,
    Depends(get_telegram_service),
]


def get_cep_service() -> CepService:
    return CepService(cep_client=CepClient())


CepServiceDep = Annotated[
    CepService,
    Depends(get_cep_service),
]


def get_telegram_webhook_service(  # noqa: PLR0913, PLR0917
    telegram_service_dep: TelegramServiceDep,
    master_service_dep: MasterServiceDep,
    onboarding_service_dep: OnboardingServiceDep,
    modality_service_dep: ModalityServiceDep,
    student_service_dep: StudentServiceDep,
    cep_service_dep: CepServiceDep,
    telegram_conversation_state_service_dep: (
        TelegramConversationStateServiceDep
    ),
) -> TelegramWebhookService:
    return TelegramWebhookService(
        telegram_service=telegram_service_dep,
        master_service=master_service_dep,
        onboarding_service=onboarding_service_dep,
        modality_service=modality_service_dep,
        student_service=student_service_dep,
        cep_service=cep_service_dep,
        telegram_conversation_state_service=(
            telegram_conversation_state_service_dep
        ),
    )


TelegramWebhookServiceDep = Annotated[
    TelegramWebhookService,
    Depends(get_telegram_webhook_service),
]
