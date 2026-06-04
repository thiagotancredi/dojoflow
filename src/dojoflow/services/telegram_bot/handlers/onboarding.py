from typing import Any

from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.schemas.onboarding import OnboardingCreate
from dojoflow.services.onboarding import OnboardingService
from dojoflow.services.telegram_conversation_state import (
    TelegramConversationStateService,
)
from dojoflow.shared.telegram_enums import TelegramStep


class TelegramOnboardingHandler:
    def __init__(
        self,
        telegram_service: TelegramService,
        onboarding_service: OnboardingService,
        telegram_conversation_state_service: (
            TelegramConversationStateService
        ),
    ) -> None:
        self.telegram_service = telegram_service
        self.onboarding_service = onboarding_service
        self.telegram_conversation_state_service = (
            telegram_conversation_state_service
        )

    async def process_message(
        self,
        chat_id: int,
        telegram_user_id: int,
        text: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if state is not None:
            return await self._process_existing_state(
                chat_id=chat_id,
                text=text,
                state=state,
            )

        await self.start_onboarding(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        return {'status': 'onboarding_started'}

    async def start_onboarding(
        self,
        chat_id: int,
        telegram_user_id: int,
        message: str | None = None,
    ) -> None:
        await self.telegram_conversation_state_service.start_onboarding(
            telegram_user_id
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=message
            or (
                'Bem-vindo ao DojoFlow! 🥋\n\n'
                'Vamos iniciar seu cadastro.\n'
                'Qual é o nome da sua academia?'
            ),
        )

    async def _process_existing_state(
        self,
        chat_id: int,
        text: str,
        state: dict[str, Any],
    ) -> dict[str, str]:
        current_step = state['current_step']

        if current_step == TelegramStep.WAITING_ACADEMY_NAME:
            return await self._process_waiting_academy_name(
                chat_id=chat_id,
                text=text,
                state=state,
            )

        if current_step == TelegramStep.WAITING_MASTER_NAME:
            return await self._process_waiting_master_name(
                chat_id=chat_id,
                text=text,
                state=state,
            )

        await self.start_onboarding(
            chat_id=chat_id,
            telegram_user_id=state['telegram_user_id'],
            message=(
                'Não consegui identificar em qual etapa do cadastro você '
                'estava.\n\n'
                'Vamos reiniciar seu cadastro.\n'
                'Qual é o nome da sua academia?'
            ),
        )

        return {'status': 'onboarding_restarted'}

    async def _process_waiting_academy_name(
        self,
        chat_id: int,
        text: str,
        state: dict[str, Any],
    ) -> dict[str, str]:
        academy_name = text.strip()

        if not academy_name or academy_name == '/start':
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Qual é o nome da sua academia?',
            )

            return {'status': 'waiting_academy_name'}

        await self.telegram_conversation_state_service.set_waiting_master_name(
            state_id=state['id'],
            academy_name=academy_name,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                f'Academia "{academy_name}" anotada. 🥋\n\n'
                'Agora me informe seu nome.'
            ),
        )

        return {'status': 'academy_name_received'}

    async def _process_waiting_master_name(
        self,
        chat_id: int,
        text: str,
        state: dict[str, Any],
    ) -> dict[str, str]:
        master_name = text.strip()

        if not master_name or master_name == '/start':
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Agora me informe seu nome.',
            )

            return {'status': 'waiting_master_name'}

        context_data = state['context_data']
        academy_name = context_data['academy_name']

        onboarding = await self.onboarding_service.register_onboarding(
            OnboardingCreate(
                academy_name=academy_name,
                master_name=master_name,
                telegram_user_id=state['telegram_user_id'],
                phone=None,
            )
        )

        await self.telegram_conversation_state_service.complete_onboarding(
            state_id=state['id'],
            academy_id=onboarding.academy_id,
            master_id=onboarding.master_id,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Cadastro concluído com sucesso! 🥋\n\n'
                f'Academia: {academy_name}\n'
                f'Mestre: {master_name}'
            ),
        )

        return {'status': 'onboarding_completed'}
