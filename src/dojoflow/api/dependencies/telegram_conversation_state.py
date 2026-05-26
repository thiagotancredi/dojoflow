from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.repositories.telegram_conversation_state import (
    TelegramConversationStateRepository,
)
from dojoflow.services.telegram_conversation_state import (
    TelegramConversationStateService,
)


def _get_telegram_conversation_state_repository(
    db_session_dep: DbSessionDep,
) -> TelegramConversationStateRepository:
    return TelegramConversationStateRepository(
        db_session=db_session_dep,
    )


TelegramConversationStateRepositoryDep = Annotated[
    TelegramConversationStateRepository,
    Depends(_get_telegram_conversation_state_repository),
]


def _get_telegram_conversation_state_service(
    telegram_conversation_state_repository_dep: (
        TelegramConversationStateRepositoryDep
    ),
    db_session_dep: DbSessionDep,
) -> TelegramConversationStateService:
    return TelegramConversationStateService(
        telegram_conversation_state_repository=(
            telegram_conversation_state_repository_dep
        ),
        db_session=db_session_dep,
    )


TelegramConversationStateServiceDep = Annotated[
    TelegramConversationStateService,
    Depends(_get_telegram_conversation_state_service),
]
