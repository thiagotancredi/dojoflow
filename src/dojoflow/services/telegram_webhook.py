from dojoflow.integrations.telegram.schemas import (
    TelegramCallbackQuery,
    TelegramUpdate,
)
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.master import MasterService
from dojoflow.services.modality import ModalityService
from dojoflow.services.onboarding import OnboardingService
from dojoflow.services.student import StudentService
from dojoflow.services.telegram_bot.handlers.main_menu import MainMenuHandler
from dojoflow.services.telegram_bot.handlers.modalities import (
    AcademyModalitiesHandler,
)
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
from dojoflow.shared.telegram_enums import TelegramFlow, TelegramStep


class TelegramWebhookService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        telegram_service: TelegramService,
        master_service: MasterService,
        onboarding_service: OnboardingService,
        modality_service: ModalityService,
        student_service: StudentService,
        telegram_conversation_state_service: (
            TelegramConversationStateService
        ),
    ) -> None:
        self.telegram_service = telegram_service
        self.master_service = master_service
        self.modality_service = modality_service
        self.student_service = student_service
        self.telegram_conversation_state_service = (
            telegram_conversation_state_service
        )

        self.main_menu_handler = MainMenuHandler(telegram_service)
        self.students_menu_handler = StudentsMenuHandler(
            telegram_service=telegram_service,
            telegram_conversation_state_service=(
                telegram_conversation_state_service
            ),
            modality_service=modality_service,
            student_service=student_service,
        )
        self.academy_modalities_handler = AcademyModalitiesHandler(
            telegram_service=telegram_service,
            modality_service=modality_service,
        )
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
            telegram_user_id=telegram_user_id,
            text=text,
            context=context,
        )

    async def _process_registered_master_message(  # noqa: PLR0911, PLR0912
        self,
        chat_id: int,
        telegram_user_id: int,
        text: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        if context.academy_status == AcademyStatus.BLOCKED:
            await self._send_blocked_message(chat_id)

            return {'status': 'blocked'}

        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_SEARCH
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_SEARCH_NAME
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_search_message(
                chat_id=chat_id,
                search_text=text,
                state_id=state['id'],
                context=context,
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_NAME
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_name_message(
                chat_id=chat_id,
                student_name=text,
                state_id=state['id'],
                context=context,
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_NAME
        ):
            students_handler = self.students_menu_handler

            return await (
                students_handler.process_student_responsible_name_message(
                    chat_id=chat_id,
                    responsible_name=text,
                    state_id=state['id'],
                    context_data=state['context_data'],
                )
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_PHONE
        ):
            students_handler = self.students_menu_handler

            return await (
                students_handler.process_student_responsible_phone_message(
                    chat_id=chat_id,
                    phone=text,
                    state_id=state['id'],
                    context_data=state['context_data'],
                )
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_PHONE
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_phone_message(
                chat_id=chat_id,
                phone=text,
                state_id=state['id'],
                context_data=state['context_data'],
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_EMAIL
        ):
            students_handler = self.students_menu_handler

            return await (
                students_handler.process_student_responsible_email_message(
                    chat_id=chat_id,
                    email=text,
                    state_id=state['id'],
                    context_data=state['context_data'],
                )
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_EMAIL
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_email_message(
                chat_id=chat_id,
                email=text,
                state_id=state['id'],
                context_data=state['context_data'],
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_CPF
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_cpf_message(
                chat_id=chat_id,
                cpf=text,
                state_id=state['id'],
                context_data=state['context_data'],
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_INSTAGRAM
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_instagram_message(
                chat_id=chat_id,
                instagram=text,
                state_id=state['id'],
                context_data=state['context_data'],
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_BIRTH_DATE
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_birth_date_message(
                chat_id=chat_id,
                birth_date_text=text,
                state_id=state['id'],
                context_data=state['context_data'],
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_MONTHLY_FEE
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_monthly_fee_message(
                chat_id=chat_id,
                monthly_fee_text=text,
                state_id=state['id'],
                context_data=state['context_data'],
            )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_DUE_DAY
        ):
            students_handler = self.students_menu_handler

            return await students_handler.process_student_due_day_message(
                chat_id=chat_id,
                due_day_text=text,
                state_id=state['id'],
                context_data=state['context_data'],
            )

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
        try:
            await self.telegram_service.answer_callback_query(
                callback_query.id
            )
        except Exception:  # noqa: BLE001
            pass

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
            telegram_user_id=telegram_user_id,
            callback_data=callback_data,
            context=context,
        )

    async def _process_callback_with_context(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        if context.academy_status == AcademyStatus.BLOCKED:
            await self._send_blocked_message(chat_id)

            return {'status': 'blocked'}

        if callback_data == 'menu:students':
            return await self._process_students_menu_callback(
                chat_id=chat_id,
                context=context,
            )

        if callback_data.startswith('students:'):
            return await self.students_menu_handler.process_callback(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data == 'menu:academy' or callback_data.startswith(
            'academy_modalities:'
        ):
            return await self.academy_modalities_handler.process_callback(
                chat_id=chat_id,
                callback_data=callback_data,
                context=context,
            )

        return await self.main_menu_handler.process_callback(
            chat_id=chat_id,
            callback_data=callback_data,
            context=context,
        )

    async def _process_students_menu_callback(
        self,
        chat_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        has_selected_modalities = (
            await self.modality_service.has_selected_modalities(
                context.academy_id
            )
        )

        if has_selected_modalities:
            await self.students_menu_handler.send_menu(chat_id)

            return {'status': 'students_menu_sent'}

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Antes de cadastrar alunos, você precisa configurar '
                'pelo menos uma modalidade da sua academia.\n\n'
                'Selecione abaixo as modalidades que existem na sua '
                'academia 👇'
            ),
        )

        await self.academy_modalities_handler.send_selection_menu(
            chat_id=chat_id,
            context=context,
        )

        return {'status': 'academy_modalities_required_before_students'}

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
