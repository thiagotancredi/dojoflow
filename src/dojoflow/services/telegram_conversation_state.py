from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.repositories.telegram_conversation_state import (
    TelegramConversationStateRepository,
)
from dojoflow.shared.telegram_enums import TelegramFlow, TelegramStep


class TelegramConversationStateService:
    def __init__(
        self,
        telegram_conversation_state_repository: (
            TelegramConversationStateRepository
        ),
        db_session: AsyncSession,
    ) -> None:
        self.telegram_conversation_state_repository = (
            telegram_conversation_state_repository
        )
        self.db_session = db_session

    async def get_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        repository = self.telegram_conversation_state_repository

        return await repository.get_by_telegram_user_id(telegram_user_id)

    @transactional
    async def start_onboarding(
        self,
        telegram_user_id: int,
    ) -> int:
        state = await self.get_by_telegram_user_id(telegram_user_id)

        data = {
            'telegram_user_id': telegram_user_id,
            'current_flow': TelegramFlow.ONBOARDING,
            'current_step': TelegramStep.WAITING_ACADEMY_NAME,
            'context_data': {},
        }

        if state is None:
            return await self.telegram_conversation_state_repository.create(
                data
            )

        await self.telegram_conversation_state_repository.update_by_id(
            record_id=state['id'],
            data=data,
        )

        return state['id']

    @transactional
    async def set_waiting_master_name(
        self,
        state_id: int,
        academy_name: str,
    ) -> None:
        await self.telegram_conversation_state_repository.update_by_id(
            record_id=state_id,
            data={
                'current_flow': TelegramFlow.ONBOARDING,
                'current_step': TelegramStep.WAITING_MASTER_NAME,
                'context_data': {
                    'academy_name': academy_name,
                },
            },
        )

    @transactional
    async def complete_onboarding(
        self,
        state_id: int,
        academy_id: int,
        master_id: int,
    ) -> None:
        await self.telegram_conversation_state_repository.update_by_id(
            record_id=state_id,
            data={
                'academy_id': academy_id,
                'master_id': master_id,
                'current_flow': TelegramFlow.ONBOARDING,
                'current_step': TelegramStep.COMPLETED,
            },
        )

    @transactional
    async def start_student_creation(
        self,
        telegram_user_id: int,
        academy_id: int,
        master_id: int,
    ) -> int:
        state = await self.get_by_telegram_user_id(telegram_user_id)

        data = {
            'telegram_user_id': telegram_user_id,
            'academy_id': academy_id,
            'master_id': master_id,
            'current_flow': TelegramFlow.STUDENT_CREATION,
            'current_step': TelegramStep.WAITING_STUDENT_NAME,
            'context_data': {},
        }

        if state is None:
            return await self.telegram_conversation_state_repository.create(
                data
            )

        await self.telegram_conversation_state_repository.update_by_id(
            record_id=state['id'],
            data=data,
        )

        return state['id']

    @transactional
    async def update_student_creation_context(
        self,
        state_id: int,
        next_step: TelegramStep,
        context_data: dict[str, Any],
    ) -> None:
        try:
            await self.telegram_conversation_state_repository.update_by_id(
                record_id=state_id,
                data={
                    'current_flow': TelegramFlow.STUDENT_CREATION,
                    'current_step': next_step,
                    'context_data': context_data,
                },
            )
            await self.db_session.commit()
        except Exception:
            await self.db_session.rollback()
            raise

    async def update_student_search_context(
        self,
        state_id: int,
        next_step: TelegramStep,
        context_data: dict[str, Any],
    ) -> None:
        try:
            await self.telegram_conversation_state_repository.update_by_id(
                record_id=state_id,
                data={
                    'current_flow': TelegramFlow.STUDENT_SEARCH,
                    'current_step': next_step,
                    'context_data': context_data,
                },
            )
            await self.db_session.commit()
        except Exception:
            await self.db_session.rollback()
            raise

    @transactional
    async def start_student_edit(
        self,
        telegram_user_id: int,
        academy_id: int,
        master_id: int,
        student_id: int,
    ) -> int:
        state = await self.get_by_telegram_user_id(telegram_user_id)

        data = {
            'telegram_user_id': telegram_user_id,
            'academy_id': academy_id,
            'master_id': master_id,
            'current_flow': TelegramFlow.STUDENT_EDIT,
            'current_step': TelegramStep.WAITING_STUDENT_EDIT_MENU,
            'context_data': {
                'student_id': student_id,
            },
        }

        if state is None:
            return await self.telegram_conversation_state_repository.create(
                data
            )

        await self.telegram_conversation_state_repository.update_by_id(
            record_id=state['id'],
            data=data,
        )

        return state['id']

    async def update_student_edit_context(
        self,
        state_id: int,
        next_step: TelegramStep,
        context_data: dict[str, Any],
    ) -> None:
        try:
            await self.telegram_conversation_state_repository.update_by_id(
                record_id=state_id,
                data={
                    'current_flow': TelegramFlow.STUDENT_EDIT,
                    'current_step': next_step,
                    'context_data': context_data,
                },
            )
            await self.db_session.commit()
        except Exception:
            await self.db_session.rollback()
            raise

    @transactional
    async def complete_current_flow(
        self,
        state_id: int,
    ) -> None:
        await self.telegram_conversation_state_repository.update_by_id(
            record_id=state_id,
            data={
                'current_step': TelegramStep.COMPLETED,
                'context_data': {},
            },
        )
