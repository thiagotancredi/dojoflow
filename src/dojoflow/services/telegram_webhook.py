from dojoflow.integrations.telegram.schemas import (
    TelegramCallbackQuery,
    TelegramUpdate,
)
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.master import MasterService
from dojoflow.services.onboarding import OnboardingService
from dojoflow.services.telegram_bot.handlers.main_menu import MainMenuHandler
from dojoflow.services.telegram_bot.handlers.onboarding import (
    TelegramOnboardingHandler,
)
from dojoflow.services.telegram_bot.handlers.students import (
    StudentsMenuHandler,
)
from dojoflow.services.telegram_conversation_state import (
    TelegramConversationStateService,
)
from dojoflow.shared.enums import AcademyStatus


class TelegramWebhookService:
    def __init__(
        self,
        telegram_service: TelegramService,
        master_service: MasterService,
        onboarding_service: OnboardingService,
        telegram_conversation_state_service: (
            TelegramConversationStateService
        ),
    ) -> None:
        self.telegram_service = telegram_service
        self.master_service = master_service

        self.main_menu_handler = MainMenuHandler(telegram_service)
        self.students_menu_handler = StudentsMenuHandler(telegram_service)
        self.onboarding_handler = TelegramOnboardingHandler(
            telegram_service=telegram_service,
            onboarding_service=onboarding_service,
            telegram_conversation_state_service=(
                telegram_conversation_state_service
            ),
        )

    async def process_update(
        self,
        payload: TelegramUpdate,
    ) -> dict[str, str]:
        if payload.callback_query is not None:
            return await self._process_callback_query(payload.callback_query)

        if payload.message is None:
            return {'status': 'ignored'}

        chat_id = payload.message.chat.id
        telegram_user_id = payload.message.from_user.id
        text = payload.message.text or ''

        context = await self.master_service.get_context_by_telegram_user_id(
            telegram_user_id
        )

        if context is None:
            return await self.onboarding_handler.process_message(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                text=text,
            )

        return await self._process_registered_master_message(
            chat_id=chat_id,
            text=text,
            context=context,
        )

    async def _process_registered_master_message(
        self,
        chat_id: int,
        text: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        if context.academy_status == AcademyStatus.BLOCKED:
            await self._send_blocked_message(chat_id)

            return {'status': 'blocked'}

        normalized_text = text.strip().lower()

        if normalized_text in {'0', 'ajuda', 'help'}:
            await self.main_menu_handler.send_help(chat_id)

            return {'status': 'help_sent'}

        await self.main_menu_handler.send_menu(
            chat_id=chat_id,
            context=context,
        )

        return {'status': 'message_processed'}

    async def _process_callback_query(
        self,
        callback_query: TelegramCallbackQuery,
    ) -> dict[str, str]:
        await self.telegram_service.answer_callback_query(callback_query.id)

        if callback_query.message is None:
            return {'status': 'ignored'}

        chat_id = callback_query.message.chat.id
        telegram_user_id = callback_query.from_user.id
        callback_data = callback_query.data or ''

        context = await self.master_service.get_context_by_telegram_user_id(
            telegram_user_id
        )

        if context is None:
            await self.onboarding_handler.start_onboarding(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
            )

            return {'status': 'onboarding_started'}

        return await self._process_callback_with_context(
            chat_id=chat_id,
            callback_data=callback_data,
            context=context,
        )

    async def _process_callback_with_context(
        self,
        chat_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        if context.academy_status == AcademyStatus.BLOCKED:
            await self._send_blocked_message(chat_id)

            return {'status': 'blocked'}

        if callback_data == 'menu:students':
            await self.students_menu_handler.send_menu(chat_id)

            return {'status': 'students_menu_sent'}

        if callback_data.startswith('students:'):
            return await self.students_menu_handler.process_callback(
                chat_id=chat_id,
                callback_data=callback_data,
            )

        return await self.main_menu_handler.process_callback(
            chat_id=chat_id,
            callback_data=callback_data,
            context=context,
        )

    async def _send_blocked_message(
        self,
        chat_id: int,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '🔒 Sua academia está bloqueada no DojoFlow.\n\n'
                'Entre em contato com o suporte para regularizar o acesso.'
            ),
        )
