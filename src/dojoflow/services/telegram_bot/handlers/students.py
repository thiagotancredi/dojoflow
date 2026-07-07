from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.cep import CepService
from dojoflow.services.modality import ModalityService
from dojoflow.services.student import StudentService
from dojoflow.services.telegram_bot.menus.students import (
    optional_field_reply_markup,
    student_address_choice_reply_markup,
    student_address_number_reply_markup,
    student_address_reference_search_actions_rows,
    student_confirmation_reply_markup,
    student_creation_cancel_reply_markup,
    student_details_reply_markup,
    student_edit_address_number_reply_markup,
    student_edit_address_reference_search_actions_rows,
    student_edit_address_reply_markup,
    student_edit_basic_data_reply_markup,
    student_edit_confirmation_reply_markup,
    student_edit_field_confirmation_reply_markup,
    student_edit_menu_reply_markup,
    student_edit_modalities_reply_markup,
    student_edit_monthly_fee_reply_markup,
    student_edit_optional_field_reply_markup,
    student_edit_prompt_reply_markup,
    student_edit_sex_reply_markup,
    student_field_confirmation_reply_markup,
    student_modalities_reply_markup,
    student_responsible_choice_reply_markup,
    student_responsible_next_action_reply_markup,
    student_responsible_reference_search_actions_rows,
    student_responsible_relationship_reply_markup,
    student_responsible_type_reply_markup,
    student_sex_reply_markup,
    students_menu_reply_markup,
    yes_no_required_reply_markup,
    yes_no_skip_reply_markup,
)
from dojoflow.services.telegram_conversation_state import (
    TelegramConversationStateService,
)
from dojoflow.shared.telegram_enums import TelegramFlow, TelegramStep

MIN_STUDENT_NAME_LENGTH = 2
MIN_PHONE_LENGTH = 10
MAX_PHONE_LENGTH = 11
CPF_LENGTH = 11
ZIP_CODE_LENGTH = 8
MIN_INSTAGRAM_LENGTH = 2
BIRTH_DATE_FORMAT = '%d/%m/%Y'
MONEY_DECIMAL_PLACES = Decimal('0.01')
MIN_MONTHLY_FEE = Decimal('0')
MIN_DUE_DAY = 1
MAX_DUE_DAY = 28
RESPONSIBLE_REFERENCE_CALLBACK_PARTS = 3
FIELD_CONFIRM_CALLBACK_DATA = 'students:create:field:confirm'
FIELD_REWRITE_CALLBACK_DATA = 'students:create:field:rewrite'
PENDING_FIELD_CONFIRMATION_KEY = 'pending_field_confirmation'
STUDENT_EDIT_PENDING_KEY = 'pending_student_edit'
ADDRESS_SEARCH_AGAIN_CALLBACK_DATA = 'students:create:address:search_again'
ADDRESS_BACK_CALLBACK_DATA = 'students:create:address:back'
RESPONSIBLE_SEARCH_AGAIN_CALLBACK_DATA = (
    'students:create:responsible:search_again'
)
RESPONSIBLE_BACK_CALLBACK_DATA = 'students:create:responsible:back'
STUDENT_EDIT_CONFIRM_CALLBACK_DATA = 'students:edit:confirm'
STUDENT_EDIT_REWRITE_CALLBACK_DATA = 'students:edit:rewrite'
STUDENT_EDIT_BACK_CALLBACK_DATA = 'students:edit:back'
STUDENT_EDIT_CANCEL_CALLBACK_DATA = 'students:edit:cancel'
STUDENT_EDIT_FIELD_CONFIRM_CALLBACK_DATA = 'students:edit:field:confirm'
STUDENT_EDIT_FIELD_REWRITE_CALLBACK_DATA = 'students:edit:field:rewrite'
STUDENT_EDIT_FIELD_CONFIRMATION_KEY = (
    'pending_student_edit_field_confirmation'
)


class StudentsMenuHandler:  # noqa: PLR0904
    def __init__(
        self,
        telegram_service: TelegramService,
        telegram_conversation_state_service: (
            TelegramConversationStateService
        ),
        modality_service: ModalityService,
        student_service: StudentService,
        cep_service: CepService,
    ) -> None:
        self.telegram_service = telegram_service
        self.telegram_conversation_state_service = (
            telegram_conversation_state_service
        )
        self.modality_service = modality_service
        self.student_service = student_service
        self.cep_service = cep_service

    async def send_menu(
        self,
        chat_id: int,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=('👥 Alunos\n\nEscolha uma opção abaixo 👇'),
            reply_markup=students_menu_reply_markup(),
        )

    async def process_callback(  # noqa: PLR0911, PLR0912
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        if callback_data == 'students:create':
            return await self._start_student_creation(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                context=context,
            )

        if callback_data == 'students:list':
            return await self._process_students_list(
                chat_id=chat_id,
                context=context,
            )

        if callback_data == 'students:search':
            return await self._start_student_search(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
            )

        if callback_data.startswith('students:details:'):
            return await self._process_student_details(
                chat_id=chat_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data in {
            'students:edit:section:basic',
            'students:edit:section:address',
            'students:edit:section:responsibles',
            'students:edit:section:monthly_fee',
            'students:edit:section:status',
            'students:edit:address:new',
            'students:edit:address:reuse',
            'students:edit:address:remove',
            'students:edit:address:search_again',
            'students:edit:address:back',
            'students:edit:address:change_zip',
            'students:edit:address:skip',
            'students:edit:back:details',
            'students:edit:back:menu',
            STUDENT_EDIT_BACK_CALLBACK_DATA,
            STUDENT_EDIT_CANCEL_CALLBACK_DATA,
            STUDENT_EDIT_CONFIRM_CALLBACK_DATA,
            STUDENT_EDIT_REWRITE_CALLBACK_DATA,
            STUDENT_EDIT_FIELD_CONFIRM_CALLBACK_DATA,
            STUDENT_EDIT_FIELD_REWRITE_CALLBACK_DATA,
        }:
            return await self._process_student_edit_callback(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:edit:field:'):
            return await self._process_student_edit_field_selection(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:edit:monthly_fee:'):
            return await self._process_student_edit_monthly_fee_selection(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:edit:address:reference:'):
            return await self._process_student_edit_address_reference_selected(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:edit:remove:'):
            return await self._process_student_edit_remove_selection(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:edit:modality:'):
            return await self._process_student_edit_modality_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:edit:sex:'):
            return await self._process_student_edit_sex_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if (
            callback_data.startswith('students:edit:')
            and self._get_id_from_callback(callback_data) is not None
        ):
            return await self._start_student_edit(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data == 'students:create:cancel':
            return await self._cancel_student_creation(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
            )

        if callback_data in {
            FIELD_CONFIRM_CALLBACK_DATA,
            FIELD_REWRITE_CALLBACK_DATA,
        }:
            return await self._process_field_confirmation_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:create:modality:'):
            return await self._process_modality_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        if callback_data.startswith('students:create:sex:'):
            return await self._process_sex_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data in {
            'students:create:responsible:self',
            'students:create:responsible:external',
        }:
            return await self._process_responsible_type_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data in {
            'students:create:responsible:new',
            'students:create:responsible:reuse',
            RESPONSIBLE_SEARCH_AGAIN_CALLBACK_DATA,
            RESPONSIBLE_BACK_CALLBACK_DATA,
        }:
            return await self._process_responsible_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data.startswith(
            'students:create:responsible:reference_all:'
        ):
            return await self._process_responsible_reference_all_selected(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                context=context,
                callback_data=callback_data,
            )

        if callback_data.startswith(
            'students:create:responsible:reference_one:'
        ):
            return await self._process_responsible_reference_one_selected(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                context=context,
                callback_data=callback_data,
            )

        if callback_data.startswith('students:create:responsible:reference:'):
            return await self._process_responsible_reference_selected(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                context=context,
                callback_data=callback_data,
            )

        if callback_data.startswith(
            'students:create:responsible:relationship:'
        ):
            return await self._process_responsible_relationship_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data.startswith('students:create:responsible:whatsapp:'):
            return await self._process_responsible_whatsapp_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data in {
            'students:create:responsible:add',
            'students:create:responsible:continue',
        }:
            return await self._process_responsible_next_action_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data == 'students:create:address:change_zip':
            return await self._process_address_change_zip(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
            )

        if callback_data in {
            'students:create:address:new',
            'students:create:address:reuse',
            'students:create:address:skip',
            ADDRESS_SEARCH_AGAIN_CALLBACK_DATA,
            ADDRESS_BACK_CALLBACK_DATA,
        }:
            return await self._process_address_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data.startswith('students:create:address:reference:'):
            return await self._process_address_reference_selected(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                context=context,
                callback_data=callback_data,
            )

        if callback_data.startswith('students:create:whatsapp:'):
            return await self._process_whatsapp_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data == 'students:create:skip':
            return await self._process_skip(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
            )

        if callback_data.startswith('students:create:exempt:'):
            return await self._process_is_exempt_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data == 'students:create:confirm':
            return await self._process_confirmation(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                context=context,
            )

        students_option_messages = {
            'students:list': (
                '📋 Lista de alunos\n\n'
                'Aqui vamos listar os alunos cadastrados na academia.\n\n'
                'Esse fluxo será implementado depois.'
            ),
            'students:search': (
                '🔎 Procurar aluno pelo nome\n\n'
                'Aqui vamos buscar um aluno específico pelo nome.\n\n'
                'Esse fluxo será implementado depois.'
            ),
        }

        message = students_option_messages.get(callback_data)

        if message is None:
            await self.send_menu(chat_id)

            return {'status': 'unknown_students_callback'}

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=students_menu_reply_markup(),
        )

        return {'status': 'students_option_selected'}

    async def _process_students_list(
        self,
        chat_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        students = await self.student_service.list_by_academy(
            academy_id=context.academy_id,
        )

        if not students:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    '📋 Lista de alunos\n\n'
                    'Ainda não há alunos cadastrados nesta academia.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'students_list_empty'}

        inline_keyboard: list[list[dict[str, str]]] = []

        for student in students:
            inline_keyboard.append([
                {
                    'text': f'ℹ️ {student.name}',
                    'callback_data': f'students:details:{student.id}',
                },
            ])

        inline_keyboard.append([
            {
                'text': '🔙 Voltar ao menu',
                'callback_data': 'menu:students',
            },
        ])

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '📋 Lista de alunos\n\n'
                'Toque em um aluno para ver as informações.'
            ),
            reply_markup={'inline_keyboard': inline_keyboard},
        )

        return {'status': 'students_list_sent'}

    async def _start_student_search(
        self,
        chat_id: int,
        telegram_user_id: int,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if state is None:
            await self.send_menu(chat_id)

            return {'status': 'student_search_state_not_found'}

        await state_service.update_student_search_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_SEARCH_NAME,
            context_data={},
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '🔎 Procurar aluno pelo nome\n\n'
                'Digite o nome ou parte do nome do aluno.'
            ),
        )

        return {'status': 'waiting_student_search_name'}

    async def process_student_search_message(
        self,
        chat_id: int,
        search_text: str,
        state_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_search_text = ' '.join(search_text.strip().split())

        if len(normalized_search_text) < MIN_STUDENT_NAME_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Digite pelo menos 2 caracteres para pesquisar.\n\n'
                    'Exemplo:\n'
                    'João'
                ),
            )

            return {'status': 'invalid_student_search_text'}

        students = await self.student_service.search_by_name(
            academy_id=context.academy_id,
            search_text=normalized_search_text,
        )

        if not students:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    '🔎 Resultado da pesquisa\n\n'
                    f'Não encontrei nenhum aluno com o nome '
                    f'"{normalized_search_text}".\n\n'
                    'Você pode pesquisar novamente ou voltar ao menu.'
                ),
                reply_markup={
                    'inline_keyboard': [
                        [
                            {
                                'text': '🔎 Pesquisar novamente',
                                'callback_data': 'students:search',
                            },
                        ],
                        [
                            {
                                'text': '🔙 Voltar ao menu',
                                'callback_data': 'menu:students',
                            },
                        ],
                    ],
                },
            )

            return {'status': 'students_search_empty'}

        await self.telegram_conversation_state_service.complete_current_flow(
            state_id,
        )

        inline_keyboard: list[list[dict[str, str]]] = []

        for student in students:
            inline_keyboard.append([
                {
                    'text': f'ℹ️ {student.name}',
                    'callback_data': f'students:details:{student.id}',
                },
            ])

        inline_keyboard.append([
            {
                'text': '🔙 Voltar ao menu',
                'callback_data': 'menu:students',
            },
        ])

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '🔎 Resultado da pesquisa\n\n'
                'Toque em um aluno para ver as informações.'
            ),
            reply_markup={'inline_keyboard': inline_keyboard},
        )

        return {'status': 'students_search_sent'}

    async def _process_student_details(
        self,
        chat_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        student_id = self._get_student_id_from_details_callback(
            callback_data,
        )

        if student_id is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_details'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=student_id,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=self._build_student_details_message(details),
            reply_markup=student_details_reply_markup(student_id),
        )

        return {'status': 'student_details_sent'}

    async def _start_student_edit(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        student_id = self._get_id_from_callback(callback_data)

        if student_id is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_edit'}

        await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=student_id,
        )

        await self.telegram_conversation_state_service.start_student_edit(
            telegram_user_id=telegram_user_id,
            academy_id=context.academy_id,
            master_id=context.master_id,
            student_id=student_id,
        )

        await self._show_student_edit_menu(chat_id)

        return {'status': 'waiting_student_edit_menu'}

    async def _show_student_edit_menu(
        self,
        chat_id: int,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='✏️ Editar aluno\n\nO que deseja editar?',
            reply_markup=student_edit_menu_reply_markup(),
        )

    async def _show_student_edit_basic_data_menu(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_BASIC_DATA,
            context_data=self._clear_student_edit_pending(context_data),
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=('👤 Dados do aluno\n\nEscolha o campo que deseja editar:'),
            reply_markup=student_edit_basic_data_reply_markup(),
        )

        return {'status': 'waiting_student_edit_basic_data'}

    async def _show_student_edit_address_menu(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        student_id = int(context_data['student_id'])
        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=student_id,
        )
        address = details.get('address')

        state_service = self.telegram_conversation_state_service
        updated_context_data = self._clear_student_edit_pending(context_data)
        updated_context_data = self._clear_student_edit_address_context(
            updated_context_data
        )

        await state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU,
            context_data=updated_context_data,
        )

        if isinstance(address, dict):
            text = (
                '🏠 Endereço\n\n'
                'Endereço atual:\n'
                f'{self._format_address_for_confirmation(address)}\n\n'
                'O que deseja fazer?'
            )
        else:
            text = (
                '🏠 Endereço\n\n'
                'Este aluno ainda não possui endereço informado.\n\n'
                'O que deseja fazer?'
            )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=student_edit_address_reply_markup(
                has_address=isinstance(address, dict)
            ),
        )

        return {'status': 'waiting_student_edit_address_menu'}

    async def _show_student_edit_monthly_fee_menu(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE_MENU,
            context_data=self._clear_student_edit_pending(context_data),
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='💰 Mensalidade\n\nEscolha o campo que deseja editar:',
            reply_markup=student_edit_monthly_fee_reply_markup(),
        )

        return {'status': 'waiting_student_edit_monthly_fee_menu'}

    async def _process_student_edit_callback(  # noqa: PLR0911, PLR0912
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        context_data = dict(state['context_data'])
        student_id = self._get_student_id_from_state(state)

        if student_id is None:
            await self.send_menu(chat_id)

            return {'status': 'student_edit_student_not_found'}

        if callback_data == 'students:edit:back:details':
            await (
                self.telegram_conversation_state_service.complete_current_flow(
                    state['id']
                )
            )
            return await self._send_student_details(
                chat_id=chat_id,
                context=context,
                student_id=student_id,
            )

        if callback_data == 'students:edit:back:menu':
            state_service = self.telegram_conversation_state_service

            await state_service.update_student_edit_context(
                state_id=state['id'],
                next_step=TelegramStep.WAITING_STUDENT_EDIT_MENU,
                context_data=self._clear_student_edit_pending(context_data),
            )
            await self._show_student_edit_menu(chat_id)
            return {'status': 'waiting_student_edit_menu'}

        if callback_data == STUDENT_EDIT_BACK_CALLBACK_DATA:
            if self._should_show_student_edit_address_menu(
                state['current_step'],
                context_data,
            ):
                return await self._show_student_edit_address_menu(
                    chat_id=chat_id,
                    state_id=state['id'],
                    context_data=context_data,
                    context=context,
                )

            if self._should_show_student_edit_monthly_fee_menu(
                state['current_step'],
                context_data,
            ):
                return await self._show_student_edit_monthly_fee_menu(
                    chat_id=chat_id,
                    state_id=state['id'],
                    context_data=context_data,
                )

            return await self._show_student_edit_basic_data_menu(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data == STUDENT_EDIT_CANCEL_CALLBACK_DATA:
            return await self._cancel_student_edit(
                chat_id=chat_id,
                state_id=state['id'],
                student_id=student_id,
                context=context,
            )

        if callback_data == STUDENT_EDIT_CONFIRM_CALLBACK_DATA:
            return await self._confirm_student_edit(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                context=context,
                student_id=student_id,
            )

        if callback_data == STUDENT_EDIT_REWRITE_CALLBACK_DATA:
            return await self._rewrite_student_edit(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data == STUDENT_EDIT_FIELD_CONFIRM_CALLBACK_DATA:
            return await self._confirm_student_edit_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data == STUDENT_EDIT_FIELD_REWRITE_CALLBACK_DATA:
            return await self._rewrite_student_edit_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data == 'students:edit:section:basic':
            return await self._show_student_edit_basic_data_menu(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data == 'students:edit:section:address':
            return await self._show_student_edit_address_menu(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                context=context,
            )

        if callback_data == 'students:edit:section:monthly_fee':
            return await self._show_student_edit_monthly_fee_menu(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data.startswith('students:edit:address:'):
            return await self._process_student_edit_address_callback(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
                context=context,
            )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Esse fluxo será implementado em seguida.',
        )

        return {'status': 'student_edit_future_flow'}

    async def _process_student_edit_field_selection(  # noqa: PLR0911
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        field = callback_data.removeprefix('students:edit:field:')
        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        student_id = self._get_student_id_from_state(state)

        if student_id is None:
            await self.send_menu(chat_id)

            return {'status': 'student_edit_student_not_found'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=student_id,
        )
        context_data = self._clear_student_edit_pending(
            dict(state['context_data'])
        )

        if field == 'name':
            return await self._ask_student_edit_text_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_NAME,
                text=(
                    'Nome atual:\n'
                    f'{details["student"]["name"]}\n\n'
                    'Digite o novo nome do aluno.'
                ),
            )

        if field == 'cpf':
            return await self._ask_student_edit_text_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_CPF,
                text=(
                    'CPF atual:\n'
                    f'{self._format_edit_cpf(details["student"].get("cpf"))}\n\n'
                    'Digite o novo CPF do aluno.\n\n'
                    'Digite apenas os números, sem pontos ou traços.\n\n'
                    'Exemplo:\n12345678911'
                ),
                remove_callback_data='students:edit:remove:cpf',
            )

        if field == 'instagram':
            return await self._ask_student_edit_text_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_INSTAGRAM,
                text=(
                    'Instagram atual:\n'
                    f'{self._format_edit_instagram(details["student"].get("instagram"))}\n\n'
                    'Digite o novo Instagram do aluno.'
                ),
                remove_callback_data='students:edit:remove:instagram',
            )

        if field == 'birth_date':
            return await self._ask_student_edit_text_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_BIRTH_DATE,
                text=(
                    'Data de nascimento atual:\n'
                    f'{self._format_birth_date_for_display(details["student"].get("birth_date"))}\n\n'
                    'Digite a nova data de nascimento do aluno.\n\n'
                    'Formato: DD/MM/AAAA'
                ),
                remove_callback_data='students:edit:remove:birth_date',
            )

        if field == 'email':
            return await self._ask_student_edit_text_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_EMAIL,
                text=(
                    'E-mail atual:\n'
                    f'{details["student"].get("email") or "Não informado"}\n\n'
                    'Digite o novo e-mail do aluno.'
                ),
                remove_callback_data='students:edit:remove:email',
            )

        if field == 'modality':
            modalities = await self.modality_service.list_selected_by_academy(
                context.academy_id
            )
            state_service = self.telegram_conversation_state_service

            await state_service.update_student_edit_context(
                state_id=state['id'],
                next_step=TelegramStep.WAITING_STUDENT_EDIT_MODALITY,
                context_data=context_data,
            )
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Modalidade atual:\n'
                    f'{self._get_student_current_modality_name(details)}\n\n'
                    'Escolha a nova modalidade do aluno.'
                ),
                reply_markup=student_edit_modalities_reply_markup(modalities),
            )
            return {'status': 'waiting_student_edit_modality'}

        if field == 'sex':
            state_service = self.telegram_conversation_state_service

            await state_service.update_student_edit_context(
                state_id=state['id'],
                next_step=TelegramStep.WAITING_STUDENT_EDIT_SEX,
                context_data=context_data,
            )
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Sexo atual:\n'
                    f'{self._format_sex(details["student"].get("sex"))}\n\n'
                    'Escolha o novo sexo do aluno.'
                ),
                reply_markup=student_edit_sex_reply_markup(),
            )
            return {'status': 'waiting_student_edit_sex'}

        await self.send_menu(chat_id)

        return {'status': 'invalid_student_edit_field'}

    async def _process_student_edit_monthly_fee_selection(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        field = callback_data.removeprefix('students:edit:monthly_fee:')
        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        student_id = self._get_student_id_from_state(state)

        if student_id is None:
            await self.send_menu(chat_id)

            return {'status': 'student_edit_student_not_found'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=student_id,
        )
        enrollment = self._get_student_current_enrollment(details)
        context_data = self._clear_student_edit_pending(
            dict(state['context_data'])
        )

        if field == 'monthly_fee':
            return await self._ask_student_edit_text_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE,
                text=(
                    'Valor atual:\n'
                    f'{self._format_edit_monthly_fee(enrollment.get("monthly_fee"))}\n\n'
                    'Digite o novo valor da mensalidade.'
                ),
            )

        if field == 'due_day':
            return await self._ask_student_edit_text_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_DUE_DAY,
                text=(
                    'Dia de vencimento atual:\n'
                    f'{self._format_edit_due_day(enrollment.get("due_day"))}\n\n'
                    'Digite o novo dia de vencimento.'
                ),
            )

        await self.send_menu(chat_id)

        return {'status': 'invalid_student_edit_monthly_fee_field'}

    async def _process_student_edit_address_callback(  # noqa: PLR0911
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        context_data = dict(state['context_data'])

        if callback_data == 'students:edit:address:new':
            student_id = self._get_student_id_from_state(state)

            if student_id is None:
                await self.send_menu(chat_id)
                return {'status': 'student_edit_student_not_found'}

            details = await self.student_service.get_details(
                academy_id=context.academy_id,
                student_id=student_id,
            )
            updated_context_data = self._clear_student_edit_address_context(
                context_data
            )
            updated_context_data['edit_current_address'] = details.get(
                'address'
            )
            return await self._ask_student_edit_address_zip_code(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=updated_context_data,
            )

        if callback_data == 'students:edit:address:reuse':
            updated_context_data = self._clear_student_edit_address_context(
                context_data
            )
            return await self._prompt_student_edit_address_reference_search(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=updated_context_data,
            )

        if callback_data == 'students:edit:address:search_again':
            updated_context_data = self._clear_student_edit_address_context(
                context_data
            )
            return await self._prompt_student_edit_address_reference_search(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=updated_context_data,
            )

        if callback_data == 'students:edit:address:back':
            return await self._show_student_edit_address_menu(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                context=context,
            )

        if callback_data == 'students:edit:address:remove':
            student_id = self._get_student_id_from_state(state)

            if student_id is None:
                await self.send_menu(chat_id)
                return {'status': 'student_edit_student_not_found'}

            details = await self.student_service.get_details(
                academy_id=context.academy_id,
                student_id=student_id,
            )
            address = details.get('address')

            if not isinstance(address, dict):
                return await self._show_student_edit_address_menu(
                    chat_id=chat_id,
                    state_id=state['id'],
                    context_data=context_data,
                    context=context,
                )

            return await self._request_student_edit_custom_confirmation(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=self._clear_student_edit_address_context(
                    context_data
                ),
                action='remove_address',
                source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU,
                prompt_text='students:edit:section:address',
                prompt_reply_markup={},
                confirmation_text=(
                    'Confirmar remoção do endereço?\n\n'
                    'Endereço atual:\n'
                    f'{self._format_address_for_confirmation(address)}'
                ),
                include_rewrite=False,
                confirm_label='✅ Confirmar remoção',
            )

        if callback_data == 'students:edit:address:change_zip':
            updated_context_data = self._clear_student_edit_address_draft(
                context_data
            )
            return await self._ask_student_edit_address_zip_code(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=updated_context_data,
            )

        if callback_data == 'students:edit:address:skip':
            return await self._skip_student_edit_address_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                current_step=state['current_step'],
            )

        await self.send_menu(chat_id)

        return {'status': 'invalid_student_edit_address_action'}

    async def _process_student_edit_address_reference_selected(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        student_id = self._get_student_id_from_state(state)
        reference_student_id = self._get_id_from_callback(callback_data)

        if student_id is None or reference_student_id is None:
            await self.send_menu(chat_id)
            return {'status': 'invalid_student_edit_address_reference'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=student_id,
        )
        reference_student = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=reference_student_id,
        )

        address_reference = reference_student.get('address')

        if not isinstance(address_reference, dict):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Esse aluno não possui endereço cadastrado.\n\n'
                    'O que deseja fazer?'
                ),
                reply_markup={
                    'inline_keyboard': (
                        student_edit_address_reference_search_actions_rows()
                    ),
                },
            )

            return {'status': 'student_edit_address_reference_without_data'}

        updated_context_data = self._clear_student_edit_address_context(
            dict(state['context_data'])
        )
        updated_context_data['edit_address_reference_student_id'] = (
            reference_student_id
        )

        current_address = details.get('address')
        current_address_text = self._format_address_for_confirmation(
            current_address
        )
        new_address_text = self._format_address_for_confirmation(
            address_reference
        )

        return await self._request_student_edit_custom_confirmation(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=updated_context_data,
            action='reuse_address',
            source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_REFERENCE_SEARCH,
            prompt_text=(
                'Digite o nome do aluno que já possui o endereço '
                'que deseja reutilizar.'
            ),
            prompt_reply_markup={},
            confirmation_text=(
                'Confirmar uso deste endereço?\n\n'
                'Aluno selecionado:\n'
                f'{reference_student["student"]["name"]}\n\n'
                'Endereço atual:\n'
                f'{current_address_text}\n\n'
                'Novo endereço:\n'
                f'{new_address_text}'
            ),
            include_rewrite=False,
            confirm_label='✅ Confirmar alteração',
        )

    async def _ask_student_edit_text_field(  # noqa: PLR0913, PLR0917
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        next_step: TelegramStep,
        text: str,
        remove_callback_data: str | None = None,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_edit_context(
            state_id=state_id,
            next_step=next_step,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=student_edit_prompt_reply_markup(
                remove_callback_data=remove_callback_data
            ),
        )

        return {'status': self._get_student_edit_waiting_status(next_step)}

    async def process_student_edit_name_message(
        self,
        chat_id: int,
        student_name: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_student_name = ' '.join(student_name.strip().split())

        if len(normalized_student_name) < MIN_STUDENT_NAME_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'O nome do aluno precisa ter pelo menos 2 caracteres.\n\n'
                    'Digite o novo nome do aluno novamente.'
                ),
                reply_markup=student_edit_prompt_reply_markup(),
            )

            return {'status': 'invalid_student_edit_name'}

        student = await self._get_student_for_edit(context, context_data)

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_NAME,
            field='name',
            field_label='Nome',
            current_display=student['name'],
            value=normalized_student_name,
            new_display=normalized_student_name,
            prompt_text=(
                'Nome atual:\n'
                f'{student["name"]}\n\n'
                'Digite o novo nome do aluno.'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(),
        )

    async def process_student_edit_cpf_message(
        self,
        chat_id: int,
        cpf: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_cpf = ''.join(
            character for character in cpf if character.isdigit()
        )

        if len(normalized_cpf) != CPF_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'CPF inválido.\n\n'
                    'Digite apenas os números, sem pontos ou traços.'
                ),
                reply_markup=student_edit_prompt_reply_markup(
                    remove_callback_data='students:edit:remove:cpf'
                ),
            )

            return {'status': 'invalid_student_edit_cpf'}

        student = await self._get_student_for_edit(context, context_data)

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_CPF,
            field='cpf',
            field_label='CPF',
            current_display=self._format_edit_cpf(student.get('cpf')),
            value=normalized_cpf,
            new_display=self._format_edit_cpf(normalized_cpf),
            prompt_text=(
                'CPF atual:\n'
                f'{self._format_edit_cpf(student.get("cpf"))}\n\n'
                'Digite o novo CPF do aluno.\n\n'
                'Digite apenas os números, sem pontos ou traços.\n\n'
                'Exemplo:\n12345678911'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(
                remove_callback_data='students:edit:remove:cpf'
            ),
        )

    async def process_student_edit_instagram_message(
        self,
        chat_id: int,
        instagram: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_instagram = instagram.strip().lstrip('@').strip()

        if len(normalized_instagram) < MIN_INSTAGRAM_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Instagram inválido.\n\n'
                    'Digite o novo Instagram do aluno novamente.'
                ),
                reply_markup=student_edit_prompt_reply_markup(
                    remove_callback_data='students:edit:remove:instagram'
                ),
            )

            return {'status': 'invalid_student_edit_instagram'}

        student = await self._get_student_for_edit(context, context_data)

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_INSTAGRAM,
            field='instagram',
            field_label='Instagram',
            current_display=self._format_edit_instagram(
                student.get('instagram')
            ),
            value=normalized_instagram,
            new_display=self._format_edit_instagram(normalized_instagram),
            prompt_text=(
                'Instagram atual:\n'
                f'{self._format_edit_instagram(student.get("instagram"))}\n\n'
                'Digite o novo Instagram do aluno.'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(
                remove_callback_data='students:edit:remove:instagram'
            ),
        )

    async def process_student_edit_birth_date_message(
        self,
        chat_id: int,
        birth_date_text: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        try:
            birth_date = datetime.strptime(
                birth_date_text.strip(),
                BIRTH_DATE_FORMAT,
            ).date()
        except ValueError:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Data de nascimento inválida.\n\nUse o formato DD/MM/AAAA.'
                ),
                reply_markup=student_edit_prompt_reply_markup(
                    remove_callback_data='students:edit:remove:birth_date'
                ),
            )

            return {'status': 'invalid_student_edit_birth_date'}

        student = await self._get_student_for_edit(context, context_data)

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_BIRTH_DATE,
            field='birth_date',
            field_label='Data de nascimento',
            current_display=self._format_birth_date_for_display(
                student.get('birth_date')
            ),
            value=birth_date.isoformat(),
            new_display=birth_date.strftime(BIRTH_DATE_FORMAT),
            prompt_text=(
                'Data de nascimento atual:\n'
                f'{self._format_birth_date_for_display(student.get("birth_date"))}\n\n'
                'Digite a nova data de nascimento do aluno.\n\n'
                'Formato: DD/MM/AAAA'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(
                remove_callback_data='students:edit:remove:birth_date'
            ),
        )

    async def process_student_edit_email_message(
        self,
        chat_id: int,
        email: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_email = email.strip().lower()

        if not self._is_valid_email(normalized_email):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'E-mail inválido.\n\n'
                    'Digite o novo e-mail do aluno novamente.'
                ),
                reply_markup=student_edit_prompt_reply_markup(
                    remove_callback_data='students:edit:remove:email'
                ),
            )

            return {'status': 'invalid_student_edit_email'}

        student = await self._get_student_for_edit(context, context_data)

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_EMAIL,
            field='email',
            field_label='E-mail',
            current_display=student.get('email') or 'Não informado',
            value=normalized_email,
            new_display=normalized_email,
            prompt_text=(
                'E-mail atual:\n'
                f'{student.get("email") or "Não informado"}\n\n'
                'Digite o novo e-mail do aluno.'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(
                remove_callback_data='students:edit:remove:email'
            ),
        )

    async def process_student_edit_monthly_fee_message(
        self,
        chat_id: int,
        monthly_fee_text: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        monthly_fee = self._parse_monthly_fee(monthly_fee_text)

        if monthly_fee is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Valor de mensalidade inválido.\n\n'
                    'Digite apenas o valor.\n\n'
                    'Exemplo:\n'
                    '125\n'
                    'ou\n'
                    '100,50'
                ),
                reply_markup=student_edit_prompt_reply_markup(),
            )

            return {'status': 'invalid_student_edit_monthly_fee'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=int(context_data['student_id']),
        )
        enrollment = self._get_student_current_enrollment(details)

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE,
            field='monthly_fee',
            field_label='Valor da mensalidade',
            current_display=self._format_edit_monthly_fee(
                enrollment.get('monthly_fee')
            ),
            value=str(monthly_fee),
            new_display=self._format_edit_monthly_fee(monthly_fee),
            prompt_text=(
                'Valor atual:\n'
                f'{self._format_edit_monthly_fee(enrollment.get("monthly_fee"))}\n\n'
                'Digite o novo valor da mensalidade.'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(),
        )

    async def process_student_edit_due_day_message(
        self,
        chat_id: int,
        due_day_text: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        due_day = self._parse_due_day(due_day_text)

        if due_day is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Dia de vencimento inválido.\n\n'
                    'Digite um dia entre 1 e 28.\n\n'
                    'Exemplo:\n'
                    '10'
                ),
                reply_markup=student_edit_prompt_reply_markup(),
            )

            return {'status': 'invalid_student_edit_due_day'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=int(context_data['student_id']),
        )
        enrollment = self._get_student_current_enrollment(details)

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_DUE_DAY,
            field='due_day',
            field_label='Dia de vencimento',
            current_display=self._format_edit_due_day(
                enrollment.get('due_day')
            ),
            value=due_day,
            new_display=str(due_day),
            prompt_text=(
                'Dia de vencimento atual:\n'
                f'{self._format_edit_due_day(enrollment.get("due_day"))}\n\n'
                'Digite o novo dia de vencimento.'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(),
        )

    async def process_student_edit_address_reference_search_message(
        self,
        chat_id: int,
        search_text: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_search_text = ' '.join(search_text.strip().split())

        if len(normalized_search_text) < MIN_STUDENT_NAME_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Digite pelo menos 2 caracteres para pesquisar.\n\n'
                    'Exemplo:\n'
                    'João'
                ),
            )

            return {
                'status': 'invalid_student_edit_address_reference_search_text'
            }

        students = await self.student_service.search_by_name(
            academy_id=context.academy_id,
            search_text=normalized_search_text,
        )

        if not students:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei nenhum aluno com o nome '
                    f'"{normalized_search_text}".\n\n'
                    'O que deseja fazer?'
                ),
                reply_markup={
                    'inline_keyboard': (
                        student_edit_address_reference_search_actions_rows()
                    ),
                },
            )

            return {'status': 'student_edit_address_reference_search_empty'}

        updated_context_data = self._clear_student_edit_address_context(
            context_data
        )

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_REFERENCE_SEARCH,
            context_data=updated_context_data,
            )
        )

        inline_keyboard: list[list[dict[str, str]]] = []

        for student in students:
            inline_keyboard.append([
                {
                    'text': f'🏠 {student.name}',
                    'callback_data': (
                        f'students:edit:address:reference:{student.id}'
                    ),
                },
            ])

        inline_keyboard.extend(
            student_edit_address_reference_search_actions_rows(),
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Encontrei estes alunos.\n\n'
                'Toque no aluno que possui o endereço que deseja reutilizar.'
            ),
            reply_markup={'inline_keyboard': inline_keyboard},
        )

        return {'status': 'student_edit_address_reference_search_sent'}

    async def process_student_edit_address_zip_code_message(
        self,
        chat_id: int,
        zip_code: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_zip_code = ''.join(
            character for character in zip_code if character.isdigit()
        )

        if len(normalized_zip_code) != ZIP_CODE_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'CEP inválido.\n\n'
                    'Digite apenas os 8 números do CEP.\n\n'
                    'Exemplo:\n'
                    '74230110'
                ),
                reply_markup=student_edit_prompt_reply_markup(),
            )

            return {'status': 'invalid_student_edit_address_zip_code'}

        return await self._request_student_edit_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE,
            field_label='o CEP do aluno',
            value=normalized_zip_code,
            display_value=normalized_zip_code,
            prompt_text=(
                'Digite o CEP do novo endereço.\n\n'
                'Digite apenas os números.\n\n'
                'Exemplo:\n'
                '74230110'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(),
        )

    async def process_student_edit_address_street_message(
        self,
        chat_id: int,
        street: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_street = ' '.join(street.strip().split())

        return await self._request_student_edit_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_STREET,
            field_label='o logradouro do endereço',
            value=normalized_street,
            display_value=normalized_street,
            prompt_text=(
                'Digite o logradouro do endereço.\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=student_edit_optional_field_reply_markup(),
        )

    async def process_student_edit_address_neighborhood_message(
        self,
        chat_id: int,
        neighborhood: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_neighborhood = ' '.join(neighborhood.strip().split())

        return await self._request_student_edit_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD,
            field_label='o bairro do endereço',
            value=normalized_neighborhood,
            display_value=normalized_neighborhood,
            prompt_text=(
                'Digite o bairro do endereço.\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=student_edit_optional_field_reply_markup(),
        )

    async def process_student_edit_address_number_message(
        self,
        chat_id: int,
        number: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_number = ' '.join(number.strip().split())
        normalized_number_compact = normalized_number.casefold().replace(
            ' ',
            '',
        )

        no_number_values = {'s/n', 'sn', 'semnumero', 'semnúmero'}

        if normalized_number_compact in no_number_values:
            normalized_number = 'S/N'

        if not normalized_number:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Número inválido.\n\n'
                    'Digite o número do endereço.\n\n'
                    'Exemplos:\n'
                    '123\n'
                    '3B\n'
                    'S/N'
                ),
                reply_markup=student_edit_address_number_reply_markup(),
            )

            return {'status': 'invalid_student_edit_address_number'}

        return await self._request_student_edit_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER,
            field_label='o número do endereço',
            value=normalized_number,
            display_value=normalized_number,
            prompt_text=(
                'Digite o número do endereço.\n\nExemplos:\n123\n3B\nS/N'
            ),
            prompt_reply_markup=student_edit_address_number_reply_markup(),
        )

    async def process_student_edit_address_complement_message(
        self,
        chat_id: int,
        complement: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_complement = complement.strip()

        return await self._request_student_edit_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT,
            field_label='o complemento do endereço',
            value=normalized_complement,
            display_value=normalized_complement or 'Sem complemento',
            prompt_text=(
                'Digite o complemento do endereço.\n\n'
                'Exemplo:\n'
                'Casa 2\n\n'
                'Se não tiver complemento, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=student_edit_optional_field_reply_markup(),
        )

    async def _request_student_edit_field_confirmation(  # noqa: PLR0913, PLR0917
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        source_step: TelegramStep,
        field_label: str,
        value: Any,
        display_value: str,
        prompt_text: str,
        prompt_reply_markup: dict[str, Any],
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data[STUDENT_EDIT_FIELD_CONFIRMATION_KEY] = {
            'source_step': source_step.value,
            'field_label': field_label,
            'value': value,
            'display_value': display_value,
            'prompt_text': prompt_text,
            'prompt_reply_markup': prompt_reply_markup,
        }

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_FIELD_CONFIRMATION,
            context_data=updated_context_data,
            )
        )

        await self._send_student_edit_field_confirmation_message(
            chat_id=chat_id,
            pending_field_confirmation=updated_context_data[
                STUDENT_EDIT_FIELD_CONFIRMATION_KEY
            ],
        )

        return {'status': 'waiting_student_edit_field_confirmation'}

    async def _send_student_edit_field_confirmation_message(
        self,
        chat_id: int,
        pending_field_confirmation: dict[str, Any],
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=self._build_field_confirmation_text(
                field_label=str(pending_field_confirmation['field_label']),
                display_value=str(pending_field_confirmation['display_value']),
            ),
            reply_markup=student_edit_field_confirmation_reply_markup(),
        )

    async def _resend_student_edit_field_confirmation_message(
        self,
        chat_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        pending_field_confirmation = context_data.get(
            STUDENT_EDIT_FIELD_CONFIRMATION_KEY
        )

        if not isinstance(pending_field_confirmation, dict):
            await self.send_menu(chat_id)
            return {'status': 'student_edit_field_confirmation_not_found'}

        await self._send_student_edit_field_confirmation_message(
            chat_id=chat_id,
            pending_field_confirmation=pending_field_confirmation,
        )

        return {'status': 'waiting_student_edit_field_confirmation'}

    async def _confirm_student_edit_field(  # noqa: PLR0911
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        pending_field_confirmation = context_data.get(
            STUDENT_EDIT_FIELD_CONFIRMATION_KEY
        )

        if not isinstance(pending_field_confirmation, dict):
            await self.send_menu(chat_id)
            return {'status': 'student_edit_field_confirmation_not_found'}

        source_step = self._get_pending_source_step(
            pending_field_confirmation
        )

        if source_step is None:
            await self.send_menu(chat_id)
            return {'status': 'student_edit_field_confirmation_invalid_source'}

        updated_context_data = dict(context_data)
        updated_context_data.pop(STUDENT_EDIT_FIELD_CONFIRMATION_KEY, None)
        value = pending_field_confirmation.get('value')

        if source_step == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE:
            return await self._apply_confirmed_student_edit_address_zip_code(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                zip_code=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_STREET:
            return await self._apply_confirmed_student_edit_address_street(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                street=str(value),
            )

        if (
            source_step
            == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD
        ):
            return (
                await self._apply_confirmed_student_edit_address_neighborhood(
                    chat_id=chat_id,
                    state_id=state_id,
                    context_data=updated_context_data,
                    neighborhood=str(value),
                )
            )

        if source_step == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER:
            return await self._apply_confirmed_student_edit_address_number(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                number=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT:
            return await self._apply_confirmed_student_edit_address_complement(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                complement=str(value),
            )

        await self.send_menu(chat_id)

        return {'status': 'student_edit_field_confirmation_invalid_source'}

    async def _rewrite_student_edit_field(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        pending_field_confirmation = context_data.get(
            STUDENT_EDIT_FIELD_CONFIRMATION_KEY
        )

        if not isinstance(pending_field_confirmation, dict):
            await self.send_menu(chat_id)
            return {'status': 'student_edit_field_confirmation_not_found'}

        source_step = self._get_pending_source_step(
            pending_field_confirmation
        )

        if source_step is None:
            await self.send_menu(chat_id)
            return {'status': 'student_edit_field_confirmation_invalid_source'}

        updated_context_data = dict(context_data)
        updated_context_data.pop(STUDENT_EDIT_FIELD_CONFIRMATION_KEY, None)

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=source_step,
            context_data=updated_context_data,
            )
        )

        send_kwargs: dict[str, Any] = {
            'chat_id': chat_id,
            'text': str(pending_field_confirmation['prompt_text']),
        }
        prompt_reply_markup = pending_field_confirmation.get(
            'prompt_reply_markup'
        )

        if isinstance(prompt_reply_markup, dict):
            send_kwargs['reply_markup'] = prompt_reply_markup

        await self.telegram_service.send_message(**send_kwargs)

        return {'status': self._get_student_edit_waiting_status(source_step)}

    async def _ask_student_edit_address_zip_code(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        updated_context_data = self._clear_student_edit_address_draft(
            context_data
        )

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE,
            context_data=updated_context_data,
            )
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Digite o CEP do novo endereço.\n\n'
                'Digite apenas os números.\n\n'
                'Exemplo:\n'
                '74230110'
            ),
            reply_markup=student_edit_prompt_reply_markup(),
        )

        return {'status': 'waiting_student_edit_address_zip_code'}

    async def _prompt_student_edit_address_reference_search(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_REFERENCE_SEARCH,
            context_data=context_data,
            )
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Digite o nome do aluno que já possui o endereço '
                'que deseja reutilizar.'
            ),
        )

        return {'status': 'waiting_student_edit_address_reference_search'}

    async def _apply_confirmed_student_edit_address_zip_code(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        zip_code: str,
    ) -> dict[str, str]:
        cep_address = await self.cep_service.search(zip_code)

        if cep_address is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei esse CEP.\n\n'
                    'Você pode tentar digitar outro CEP.'
                ),
                reply_markup=student_edit_prompt_reply_markup(),
            )

            return {'status': 'student_edit_address_zip_code_not_found'}

        updated_context_data = dict(context_data)
        updated_context_data['edit_address'] = {
            'zip_code': cep_address.zip_code,
            'street': cep_address.street,
            'neighborhood': cep_address.neighborhood,
            'city': cep_address.city,
            'state': cep_address.state,
        }

        if not cep_address.street:
            await (
                self.telegram_conversation_state_service.update_student_edit_context(
                state_id=state_id,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_STREET,
                context_data=updated_context_data,
                )
            )

            missing_fields_text = 'o logradouro'

            if not cep_address.neighborhood:
                missing_fields_text = 'logradouro nem bairro'

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Encontrei parcialmente este endereço:\n\n'
                    f'Cidade/Estado: {cep_address.city}/{cep_address.state}\n'
                    f'CEP: {cep_address.zip_code}\n\n'
                    f'O CEP não trouxe {missing_fields_text}.\n\n'
                    'Primeiro, digite o logradouro ou toque em "⏭️ Pular".'
                ),
                reply_markup=student_edit_optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_edit_address_street'}

        if not cep_address.neighborhood:
            await (
                self.telegram_conversation_state_service.update_student_edit_context(
                state_id=state_id,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD,
                context_data=updated_context_data,
                )
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Encontrei parcialmente este endereço:\n\n'
                    f'Logradouro: {cep_address.street}\n'
                    f'Cidade/Estado: {cep_address.city}/{cep_address.state}\n'
                    f'CEP: {cep_address.zip_code}\n\n'
                    'O CEP não trouxe o bairro.\n\n'
                    'Digite o bairro ou toque em "⏭️ Pular".'
                ),
                reply_markup=student_edit_optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_edit_address_neighborhood'}

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER,
            context_data=updated_context_data,
            )
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Encontrei este endereço:\n\n'
                f'Logradouro: {cep_address.street}\n'
                f'Bairro: {cep_address.neighborhood}\n'
                f'Cidade/Estado: {cep_address.city}/{cep_address.state}\n'
                f'CEP: {cep_address.zip_code}\n\n'
                'Agora digite o número do endereço.\n\n'
                'Exemplos:\n'
                '123\n'
                '3B\n'
                'S/N'
            ),
            reply_markup=student_edit_address_number_reply_markup(),
        )

        return {'status': 'waiting_student_edit_address_number'}

    async def _apply_confirmed_student_edit_address_street(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        street: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('edit_address', {}))
        address['street'] = street
        updated_context_data['edit_address'] = address

        if not address.get('neighborhood'):
            await (
                self.telegram_conversation_state_service.update_student_edit_context(
                state_id=state_id,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD,
                context_data=updated_context_data,
                )
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Agora digite o bairro do endereço.\n\n'
                    'Se não quiser informar agora, toque em "⏭️ Pular".'
                ),
                reply_markup=student_edit_optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_edit_address_neighborhood'}

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER,
            context_data=updated_context_data,
            )
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Agora digite o número do endereço.\n\nExemplos:\n123\n3B\nS/N'
            ),
            reply_markup=student_edit_address_number_reply_markup(),
        )

        return {'status': 'waiting_student_edit_address_number'}

    async def _apply_confirmed_student_edit_address_neighborhood(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        neighborhood: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('edit_address', {}))
        address['neighborhood'] = neighborhood
        updated_context_data['edit_address'] = address

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER,
            context_data=updated_context_data,
            )
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Agora digite o número do endereço.\n\nExemplos:\n123\n3B\nS/N'
            ),
            reply_markup=student_edit_address_number_reply_markup(),
        )

        return {'status': 'waiting_student_edit_address_number'}

    async def _apply_confirmed_student_edit_address_number(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        number: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('edit_address', {}))
        address['number'] = number
        updated_context_data['edit_address'] = address

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT,
            context_data=updated_context_data,
            )
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Digite o complemento do endereço.\n\n'
                'Exemplo:\n'
                'Casa 2\n\n'
                'Se não tiver complemento, toque em "⏭️ Pular".'
            ),
            reply_markup=student_edit_optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_edit_address_complement'}

    async def _apply_confirmed_student_edit_address_complement(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        complement: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('edit_address', {}))
        address['complement'] = complement
        updated_context_data['edit_address'] = address

        return await self._request_student_edit_new_address_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=updated_context_data,
        )

    async def _skip_student_edit_address_field(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        current_step: TelegramStep,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('edit_address', {}))

        if current_step == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_STREET:
            address['street'] = None
            updated_context_data['edit_address'] = address

            await (
                self.telegram_conversation_state_service.update_student_edit_context(
                state_id=state_id,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD,
                context_data=updated_context_data,
                )
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Agora digite o bairro do endereço.\n\n'
                    'Se não quiser informar agora, toque em "⏭️ Pular".'
                ),
                reply_markup=student_edit_optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_edit_address_neighborhood'}

        if (
            current_step
            == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD
        ):
            address['neighborhood'] = None
            updated_context_data['edit_address'] = address

            await (
                self.telegram_conversation_state_service.update_student_edit_context(
                state_id=state_id,
                next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER,
                context_data=updated_context_data,
                )
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Agora digite o número do endereço.\n\n'
                    'Exemplos:\n123\n3B\nS/N'
                ),
                reply_markup=student_edit_address_number_reply_markup(),
            )

            return {'status': 'waiting_student_edit_address_number'}

        if (
            current_step
            == TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT
        ):
            address['complement'] = None
            updated_context_data['edit_address'] = address

            return await self._request_student_edit_new_address_confirmation(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
            )

        await self.send_menu(chat_id)

        return {'status': 'invalid_student_edit_address_skip'}

    async def _request_student_edit_new_address_confirmation(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        address = context_data.get('edit_address')
        current_address = context_data.get('edit_current_address')

        if not isinstance(address, dict):
            await self.send_menu(chat_id)
            return {'status': 'student_edit_address_not_found'}

        return await self._request_student_edit_custom_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            action='update_address',
            source_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE,
            prompt_text=(
                'Digite o CEP do novo endereço.\n\n'
                'Digite apenas os números.\n\n'
                'Exemplo:\n'
                '74230110'
            ),
            prompt_reply_markup=student_edit_prompt_reply_markup(),
            confirmation_text=(
                'Confirmar novo endereço?\n\n'
                'Endereço atual:\n'
                f'{self._format_address_for_confirmation(current_address)}\n\n'
                'Novo endereço:\n'
                f'{self._format_address_for_confirmation(address)}'
            ),
            include_rewrite=True,
            rewrite_label='✏️ Reescrever endereço',
        )

    async def _request_student_edit_custom_confirmation(  # noqa: PLR0913, PLR0917
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        action: str,
        source_step: TelegramStep,
        prompt_text: str,
        prompt_reply_markup: dict[str, Any],
        confirmation_text: str,
        include_rewrite: bool,
        confirm_label: str = '✅ Confirmar alteração',
        rewrite_label: str = '✏️ Reescrever',
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data[STUDENT_EDIT_PENDING_KEY] = {
            'action': action,
            'source_step': source_step.value,
            'prompt_text': prompt_text,
            'prompt_reply_markup': prompt_reply_markup,
            'confirmation_text': confirmation_text,
            'include_rewrite': include_rewrite,
            'confirm_label': confirm_label,
            'rewrite_label': rewrite_label,
        }

        await (
            self.telegram_conversation_state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data=updated_context_data,
            )
        )

        await self._send_student_edit_confirmation_message(
            chat_id=chat_id,
            pending_edit=updated_context_data[STUDENT_EDIT_PENDING_KEY],
        )

        return {'status': 'waiting_student_edit_confirmation'}

    async def _request_student_edit_confirmation(  # noqa: PLR0913, PLR0917
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        source_step: TelegramStep,
        field: str,
        field_label: str,
        current_display: str,
        value: Any,
        new_display: str,
        prompt_text: str,
        prompt_reply_markup: dict[str, Any],
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data[STUDENT_EDIT_PENDING_KEY] = {
            'action': 'update',
            'source_step': source_step.value,
            'field': field,
            'field_label': field_label,
            'current_display': current_display,
            'value': value,
            'new_display': new_display,
            'prompt_text': prompt_text,
            'prompt_reply_markup': prompt_reply_markup,
        }

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_edit_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data=updated_context_data,
        )

        await self._send_student_edit_confirmation_message(
            chat_id=chat_id,
            pending_edit=updated_context_data[STUDENT_EDIT_PENDING_KEY],
        )

        return {'status': 'waiting_student_edit_confirmation'}

    async def _process_student_edit_remove_selection(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        field = callback_data.removeprefix('students:edit:remove:')
        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        student = await self._get_student_for_edit(
            context=context,
            context_data=state['context_data'],
        )

        field_label = self._get_student_edit_field_label(field)
        current_display = self._get_student_edit_current_display(
            field=field,
            student=student,
        )

        updated_context_data = dict(state['context_data'])
        updated_context_data[STUDENT_EDIT_PENDING_KEY] = {
            'action': 'remove',
            'field': field,
            'field_label': field_label,
            'current_display': current_display,
        }

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_edit_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION,
            context_data=updated_context_data,
        )

        await self._send_student_edit_confirmation_message(
            chat_id=chat_id,
            pending_edit=updated_context_data[STUDENT_EDIT_PENDING_KEY],
        )

        return {'status': 'waiting_student_edit_confirmation'}

    async def _process_student_edit_modality_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        modality_id = self._get_id_from_callback(callback_data)

        if modality_id is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_edit_modality'}

        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=int(state['context_data']['student_id']),
        )
        selected_modality = await self._get_selected_modality(
            academy_id=context.academy_id,
            modality_id=modality_id,
        )

        if selected_modality is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Escolha uma modalidade válida.',
            )

            return {'status': 'invalid_student_edit_modality'}

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=state['context_data'],
            source_step=TelegramStep.WAITING_STUDENT_EDIT_MODALITY,
            field='modality',
            field_label='Modalidade',
            current_display=self._get_student_current_modality_name(details),
            value=selected_modality.id,
            new_display=selected_modality.name,
            prompt_text=(
                'Modalidade atual:\n'
                f'{self._get_student_current_modality_name(details)}\n\n'
                'Escolha a nova modalidade do aluno.'
            ),
            prompt_reply_markup=student_edit_modalities_reply_markup(
                await self.modality_service.list_selected_by_academy(
                    context.academy_id
                )
            ),
        )

    async def _process_student_edit_sex_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        sex_options = {
            'students:edit:sex:male': 'male',
            'students:edit:sex:female': 'female',
            'students:edit:sex:other': 'other',
        }
        selected_sex = sex_options.get(callback_data)

        if selected_sex is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_edit_sex'}

        state = await self._get_student_edit_state(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
        )

        if state is None:
            return {'status': 'student_edit_state_not_found'}

        student = await self._get_student_for_edit(
            context=context,
            context_data=state['context_data'],
        )

        return await self._request_student_edit_confirmation(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=state['context_data'],
            source_step=TelegramStep.WAITING_STUDENT_EDIT_SEX,
            field='sex',
            field_label='Sexo',
            current_display=self._format_sex(student.get('sex')),
            value=selected_sex,
            new_display=self._format_sex(selected_sex),
            prompt_text=(
                'Sexo atual:\n'
                f'{self._format_sex(student.get("sex"))}\n\n'
                'Escolha o novo sexo do aluno.'
            ),
            prompt_reply_markup=student_edit_sex_reply_markup(),
        )

    async def _send_student_edit_confirmation_message(
        self,
        chat_id: int,
        pending_edit: dict[str, Any],
    ) -> None:
        action = pending_edit.get('action')

        if 'confirmation_text' in pending_edit:
            text = str(pending_edit['confirmation_text'])
            reply_markup = student_edit_confirmation_reply_markup(
                include_rewrite=bool(pending_edit.get('include_rewrite')),
                confirm_label=str(
                    pending_edit.get(
                        'confirm_label',
                        '✅ Confirmar alteração',
                    )
                ),
                rewrite_label=str(
                    pending_edit.get('rewrite_label', '✏️ Reescrever')
                ),
            )
        elif action == 'remove':
            text = self._build_student_edit_remove_confirmation_text(
                field_label=str(pending_edit['field_label']),
                current_display=str(pending_edit['current_display']),
            )
            reply_markup = student_edit_confirmation_reply_markup(
                include_rewrite=False
            )
        else:
            text = self._build_student_edit_update_confirmation_text(
                current_display=str(pending_edit['current_display']),
                new_display=str(pending_edit['new_display']),
                field_label=str(pending_edit['field_label']),
            )
            reply_markup = student_edit_confirmation_reply_markup()

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )

    async def _resend_student_edit_confirmation_message(
        self,
        chat_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        pending_edit = context_data.get(STUDENT_EDIT_PENDING_KEY)

        if not isinstance(pending_edit, dict):
            await self.send_menu(chat_id)

            return {'status': 'student_edit_pending_not_found'}

        await self._send_student_edit_confirmation_message(
            chat_id=chat_id,
            pending_edit=pending_edit,
        )

        return {'status': 'waiting_student_edit_confirmation'}

    async def _confirm_student_edit(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
        student_id: int,
    ) -> dict[str, str]:
        pending_edit = context_data.get(STUDENT_EDIT_PENDING_KEY)

        if not isinstance(pending_edit, dict):
            await self.send_menu(chat_id)

            return {'status': 'student_edit_pending_not_found'}

        action = pending_edit.get('action')
        field = str(pending_edit.get('field'))

        if action == 'remove':
            await self.student_service.update_basic_data(
                academy_id=context.academy_id,
                student_id=student_id,
                data={field: None},
            )
        elif action == 'update_address':
            await self.student_service.update_address(
                academy_id=context.academy_id,
                student_id=student_id,
                address_data=dict(context_data.get('edit_address', {})),
            )
        elif action == 'reuse_address':
            await self.student_service.reuse_address(
                academy_id=context.academy_id,
                student_id=student_id,
                reference_student_id=int(
                    context_data['edit_address_reference_student_id']
                ),
            )
        elif action == 'remove_address':
            await self.student_service.remove_address(
                academy_id=context.academy_id,
                student_id=student_id,
            )
        elif field == 'modality':
            await self.student_service.update_modality(
                academy_id=context.academy_id,
                student_id=student_id,
                modality_id=int(pending_edit['value']),
            )
        elif field in {'monthly_fee', 'due_day'}:
            await self.student_service.update_enrollment(
                academy_id=context.academy_id,
                student_id=student_id,
                data={
                    field: pending_edit.get('value'),
                },
            )
        else:
            await self.student_service.update_basic_data(
                academy_id=context.academy_id,
                student_id=student_id,
                data={
                    field: pending_edit.get('value'),
                },
            )

        await self.telegram_conversation_state_service.complete_current_flow(
            state_id
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Alteração salva com sucesso! ✅',
        )

        return await self._send_student_details(
            chat_id=chat_id,
            context=context,
            student_id=student_id,
            status='student_edit_saved',
        )

    async def _rewrite_student_edit(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        pending_edit = context_data.get(STUDENT_EDIT_PENDING_KEY)

        if not isinstance(pending_edit, dict):
            await self.send_menu(chat_id)

            return {'status': 'student_edit_pending_not_found'}

        source_step = self._get_student_edit_source_step(pending_edit)

        if source_step is None:
            await self.send_menu(chat_id)

            return {'status': 'student_edit_invalid_source'}

        updated_context_data = self._clear_student_edit_pending(context_data)

        if pending_edit.get('action') == 'update_address':
            updated_context_data = self._clear_student_edit_address_draft(
                updated_context_data
            )

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_edit_context(
            state_id=state_id,
            next_step=source_step,
            context_data=updated_context_data,
        )

        send_kwargs: dict[str, Any] = {
            'chat_id': chat_id,
            'text': str(pending_edit['prompt_text']),
        }

        prompt_reply_markup = pending_edit.get('prompt_reply_markup')

        if isinstance(prompt_reply_markup, dict):
            send_kwargs['reply_markup'] = prompt_reply_markup

        await self.telegram_service.send_message(**send_kwargs)

        return {'status': self._get_student_edit_waiting_status(source_step)}

    async def _cancel_student_edit(
        self,
        chat_id: int,
        state_id: int,
        student_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        await self.telegram_conversation_state_service.complete_current_flow(
            state_id
        )

        return await self._send_student_details(
            chat_id=chat_id,
            context=context,
            student_id=student_id,
            status='student_edit_cancelled',
        )

    async def _send_student_details(
        self,
        chat_id: int,
        context: MasterContextRead,
        student_id: int,
        status: str = 'student_details_sent',
    ) -> dict[str, str]:
        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=student_id,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=self._build_student_details_message(details),
            reply_markup=student_details_reply_markup(student_id),
        )

        return {'status': status}

    async def _get_student_edit_state(
        self,
        chat_id: int,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        state = await (
            self.telegram_conversation_state_service.get_by_telegram_user_id(
                telegram_user_id
            )
        )

        if (
            state is not None
            and state['current_flow'] == TelegramFlow.STUDENT_EDIT
        ):
            return state

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Não encontrei uma edição de aluno em andamento.\n\n'
                'Abra os detalhes do aluno e toque em "✏️ Editar".'
            ),
            reply_markup=students_menu_reply_markup(),
        )

        return None

    async def _get_student_for_edit(
        self,
        context: MasterContextRead,
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=int(context_data['student_id']),
        )

        return details['student']

    @staticmethod
    def _get_student_id_from_state(
        state: dict[str, Any],
    ) -> int | None:
        student_id = state['context_data'].get('student_id')

        if isinstance(student_id, int):
            return student_id

        if isinstance(student_id, str) and student_id.isdigit():
            return int(student_id)

        return None

    @staticmethod
    def _clear_student_edit_pending(
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        updated_context_data = dict(context_data)
        updated_context_data.pop(STUDENT_EDIT_PENDING_KEY, None)
        updated_context_data.pop(STUDENT_EDIT_FIELD_CONFIRMATION_KEY, None)

        return updated_context_data

    @staticmethod
    def _clear_student_edit_address_context(
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        updated_context_data = dict(context_data)

        for key in (
            'edit_address',
            'edit_current_address',
            'edit_address_reference_student_id',
            STUDENT_EDIT_FIELD_CONFIRMATION_KEY,
        ):
            updated_context_data.pop(key, None)

        return updated_context_data

    @staticmethod
    def _clear_student_edit_address_draft(
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        updated_context_data = dict(context_data)

        for key in (
            'edit_address',
            STUDENT_EDIT_FIELD_CONFIRMATION_KEY,
        ):
            updated_context_data.pop(key, None)

        return updated_context_data

    @staticmethod
    def _format_edit_cpf(
        cpf: Any,
    ) -> str:
        if not cpf:
            return 'Não informado'

        cpf_text = str(cpf)
        return f'{cpf_text[:3]}.***.***-{cpf_text[-2:]}'

    @staticmethod
    def _format_edit_instagram(
        instagram: Any,
    ) -> str:
        if not instagram:
            return 'Não informado'

        return f'@{str(instagram).lstrip("@")}'

    @staticmethod
    def _format_edit_monthly_fee(
        monthly_fee: Any,
    ) -> str:
        if monthly_fee in {None, ''}:
            return 'Não informado'

        normalized_monthly_fee = Decimal(str(monthly_fee)).quantize(
            MONEY_DECIMAL_PLACES
        )

        return f'R$ {normalized_monthly_fee}'.replace('.', ',')

    @staticmethod
    def _format_edit_due_day(
        due_day: Any,
    ) -> str:
        if due_day in {None, ''}:
            return 'Não informado'

        return str(due_day)

    @staticmethod
    def _format_address_for_confirmation(
        address: dict[str, Any] | None,
    ) -> str:
        if not isinstance(address, dict):
            return 'Não informado'

        street = address.get('street') or 'Não informado'
        number = address.get('number') or 'S/N'
        neighborhood = address.get('neighborhood') or 'Não informado'
        city = address.get('city') or 'Não informado'
        state = address.get('state') or 'Não informado'
        zip_code = address.get('zip_code') or 'Não informado'
        complement = address.get('complement') or 'Não informado'

        return (
            f'Logradouro: {street}\n'
            f'Número: {number}\n'
            f'Bairro: {neighborhood}\n'
            f'Cidade/Estado: {city}/{state}\n'
            f'CEP: {zip_code}\n'
            f'Complemento: {complement}'
        )

    @staticmethod
    def _build_student_edit_update_confirmation_text(
        *,
        field_label: str,
        current_display: str,
        new_display: str,
    ) -> str:
        return (
            f'Confirmar alteração de {field_label.lower()}?\n\n'
            f'De:\n{current_display}\n\n'
            f'Para:\n{new_display}'
        )

    @staticmethod
    def _build_student_edit_remove_confirmation_text(
        *,
        field_label: str,
        current_display: str,
    ) -> str:
        return (
            'Confirmar remoção?\n\n'
            f'Campo:\n{field_label}\n\n'
            f'Valor atual:\n{current_display}'
        )

    @staticmethod
    def _get_student_current_modality_name(
        details: dict[str, Any],
    ) -> str:
        enrollments = details.get('enrollments', [])

        if not enrollments:
            return 'Não informado'

        return str(enrollments[0].get('modality_name') or 'Não informado')

    @staticmethod
    def _get_student_edit_source_step(
        pending_edit: dict[str, Any],
    ) -> TelegramStep | None:
        source_step = pending_edit.get('source_step')

        try:
            return TelegramStep(str(source_step))
        except ValueError:
            return None

    @staticmethod
    def _get_student_edit_waiting_status(
        step: TelegramStep,
    ) -> str:
        statuses = {
            TelegramStep.WAITING_STUDENT_EDIT_NAME: (
                'waiting_student_edit_name'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_MODALITY: (
                'waiting_student_edit_modality'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_SEX: (
                'waiting_student_edit_sex'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_CPF: (
                'waiting_student_edit_cpf'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_INSTAGRAM: (
                'waiting_student_edit_instagram'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_BIRTH_DATE: (
                'waiting_student_edit_birth_date'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_EMAIL: (
                'waiting_student_edit_email'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE: (
                'waiting_student_edit_address_zip_code'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_STREET: (
                'waiting_student_edit_address_street'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD: (
                'waiting_student_edit_address_neighborhood'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER: (
                'waiting_student_edit_address_number'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT: (
                'waiting_student_edit_address_complement'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE: (
                'waiting_student_edit_monthly_fee'
            ),
            TelegramStep.WAITING_STUDENT_EDIT_DUE_DAY: (
                'waiting_student_edit_due_day'
            ),
        }

        return statuses.get(step, 'waiting_student_edit')

    @staticmethod
    def _get_student_edit_field_label(
        field: str,
    ) -> str:
        labels = {
            'cpf': 'CPF',
            'instagram': 'Instagram',
            'birth_date': 'Data de nascimento',
            'email': 'E-mail',
        }

        return labels.get(field, field)

    def _get_student_edit_current_display(
        self,
        field: str,
        student: dict[str, Any],
    ) -> str:
        if field == 'cpf':
            return self._format_edit_cpf(student.get('cpf'))

        if field == 'instagram':
            return self._format_edit_instagram(student.get('instagram'))

        if field == 'birth_date':
            return self._format_birth_date_for_display(
                student.get('birth_date')
            )

        return str(student.get(field) or 'Não informado')

    @staticmethod
    def _should_show_student_edit_monthly_fee_menu(
        current_step: TelegramStep,
        context_data: dict[str, Any],
    ) -> bool:
        if current_step in {
            TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE_MENU,
            TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE,
            TelegramStep.WAITING_STUDENT_EDIT_DUE_DAY,
        }:
            return True

        if current_step != TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION:
            return False

        pending_edit = context_data.get(STUDENT_EDIT_PENDING_KEY)

        if not isinstance(pending_edit, dict):
            return False

        source_step = StudentsMenuHandler._get_student_edit_source_step(
            pending_edit
        )

        return source_step in {
            TelegramStep.WAITING_STUDENT_EDIT_MONTHLY_FEE,
            TelegramStep.WAITING_STUDENT_EDIT_DUE_DAY,
        }

    @staticmethod
    def _should_show_student_edit_address_menu(
        current_step: TelegramStep,
        context_data: dict[str, Any],
    ) -> bool:
        if current_step in {
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU,
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_REFERENCE_SEARCH,
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE,
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_STREET,
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD,
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER,
            TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT,
        }:
            return True

        if (
            current_step
            == TelegramStep.WAITING_STUDENT_EDIT_FIELD_CONFIRMATION
        ):
            pending_field_confirmation = context_data.get(
                STUDENT_EDIT_FIELD_CONFIRMATION_KEY
            )

            if not isinstance(pending_field_confirmation, dict):
                return False

            source_step = StudentsMenuHandler._get_pending_source_step(
                pending_field_confirmation
            )

            return source_step in {
                TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_ZIP_CODE,
                TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_STREET,
                TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NEIGHBORHOOD,
                TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_NUMBER,
                TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_COMPLEMENT,
            }

        if current_step != TelegramStep.WAITING_STUDENT_EDIT_CONFIRMATION:
            return False

        pending_edit = context_data.get(STUDENT_EDIT_PENDING_KEY)

        if not isinstance(pending_edit, dict):
            return False

        return str(pending_edit.get('action')) in {
            'update_address',
            'reuse_address',
            'remove_address',
        }

    @staticmethod
    def _get_student_current_enrollment(
        details: dict[str, Any],
    ) -> dict[str, Any]:
        enrollments = details.get('enrollments', [])

        if not enrollments:
            return {}

        return dict(enrollments[0])

    @staticmethod
    def _parse_monthly_fee(
        monthly_fee_text: str,
    ) -> Decimal | None:
        normalized_monthly_fee = monthly_fee_text.strip().replace(',', '.')

        try:
            monthly_fee = Decimal(normalized_monthly_fee)
        except InvalidOperation:
            return None

        if monthly_fee <= MIN_MONTHLY_FEE:
            return None

        return monthly_fee.quantize(MONEY_DECIMAL_PLACES)

    @staticmethod
    def _parse_due_day(
        due_day_text: str,
    ) -> int | None:
        try:
            due_day = int(due_day_text.strip())
        except ValueError:
            return None

        if not MIN_DUE_DAY <= due_day <= MAX_DUE_DAY:
            return None

        return due_day

    async def _request_field_confirmation(  # noqa: PLR0913, PLR0917
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        source_step: TelegramStep,
        field_label: str,
        value: Any,
        display_value: str,
        prompt_text: str,
        prompt_reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data[PENDING_FIELD_CONFIRMATION_KEY] = {
            'source_step': source_step.value,
            'field_label': field_label,
            'value': value,
            'display_value': display_value,
            'prompt_text': prompt_text,
            'prompt_reply_markup': prompt_reply_markup,
        }

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION,
            context_data=updated_context_data,
        )

        await self._send_field_confirmation_message(
            chat_id=chat_id,
            pending_field_confirmation=updated_context_data[
                PENDING_FIELD_CONFIRMATION_KEY
            ],
        )

        return {'status': 'waiting_student_field_confirmation'}

    async def _send_field_confirmation_message(
        self,
        chat_id: int,
        pending_field_confirmation: dict[str, Any],
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=self._build_field_confirmation_text(
                field_label=str(
                    pending_field_confirmation.get('field_label', 'o campo')
                ),
                display_value=str(
                    pending_field_confirmation.get('display_value', '')
                ),
            ),
            reply_markup=student_field_confirmation_reply_markup(),
        )

    async def _resend_field_confirmation_message(
        self,
        chat_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        pending_field_confirmation = context_data.get(
            PENDING_FIELD_CONFIRMATION_KEY
        )

        if not isinstance(pending_field_confirmation, dict):
            await self.send_menu(chat_id)

            return {'status': 'student_field_confirmation_not_found'}

        await self._send_field_confirmation_message(
            chat_id=chat_id,
            pending_field_confirmation=pending_field_confirmation,
        )

        return {'status': 'waiting_student_field_confirmation'}

    async def _process_field_confirmation_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_field_confirmation(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei uma confirmação de campo aguardando '
                    'resposta.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_field_confirmation_state_not_found'}

        context_data = dict(state['context_data'])
        pending_field_confirmation = context_data.get(
            PENDING_FIELD_CONFIRMATION_KEY
        )

        if not isinstance(pending_field_confirmation, dict):
            await self.send_menu(chat_id)

            return {'status': 'student_field_confirmation_not_found'}

        if callback_data == FIELD_REWRITE_CALLBACK_DATA:
            return await self._rewrite_pending_field(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
                pending_field_confirmation=pending_field_confirmation,
            )

        return await self._confirm_pending_field(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
            pending_field_confirmation=pending_field_confirmation,
            context=context,
        )

    async def _rewrite_pending_field(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        pending_field_confirmation: dict[str, Any],
    ) -> dict[str, str]:
        source_step = self._get_pending_source_step(
            pending_field_confirmation,
        )

        if source_step is None:
            await self.send_menu(chat_id)

            return {'status': 'student_field_confirmation_invalid_source'}

        updated_context_data = dict(context_data)
        updated_context_data.pop(PENDING_FIELD_CONFIRMATION_KEY, None)

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=source_step,
            context_data=updated_context_data,
        )

        send_message_kwargs: dict[str, Any] = {
            'chat_id': chat_id,
            'text': str(pending_field_confirmation['prompt_text']),
        }
        prompt_reply_markup = pending_field_confirmation.get(
            'prompt_reply_markup'
        )

        if isinstance(prompt_reply_markup, dict):
            send_message_kwargs['reply_markup'] = prompt_reply_markup

        await self.telegram_service.send_message(**send_message_kwargs)

        return {'status': self._get_waiting_status_for_step(source_step)}

    async def _confirm_pending_field(  # noqa: PLR0911, PLR0912
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        pending_field_confirmation: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        source_step = self._get_pending_source_step(
            pending_field_confirmation,
        )

        if source_step is None:
            await self.send_menu(chat_id)

            return {'status': 'student_field_confirmation_invalid_source'}

        updated_context_data = dict(context_data)
        updated_context_data.pop(PENDING_FIELD_CONFIRMATION_KEY, None)
        value = pending_field_confirmation.get('value')

        if source_step == TelegramStep.WAITING_STUDENT_NAME:
            return await self._apply_confirmed_student_name(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                context=context,
                student_name=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_PHONE:
            return await self._apply_confirmed_student_phone(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                phone=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_RESPONSIBLE_NAME:
            return await self._apply_confirmed_student_responsible_name(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                responsible_name=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_RESPONSIBLE_PHONE:
            return await self._apply_confirmed_student_responsible_phone(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                phone=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_RESPONSIBLE_EMAIL:
            return await self._apply_confirmed_student_responsible_email(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                email=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_ADDRESS_ZIP_CODE:
            return await self._apply_confirmed_student_address_zip_code(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                zip_code=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_ADDRESS_STREET:
            return await self._apply_confirmed_student_address_street(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                street=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD:
            return await self._apply_confirmed_student_address_neighborhood(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                neighborhood=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER:
            return await self._apply_confirmed_student_address_number(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                number=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_ADDRESS_COMPLEMENT:
            return await self._apply_confirmed_student_address_complement(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                complement=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_CPF:
            return await self._apply_confirmed_student_cpf(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                cpf=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_INSTAGRAM:
            return await self._apply_confirmed_student_instagram(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                instagram=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_EMAIL:
            return await self._apply_confirmed_student_email(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                email=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_BIRTH_DATE:
            return await self._apply_confirmed_student_birth_date(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                birth_date=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_MONTHLY_FEE:
            return await self._apply_confirmed_student_monthly_fee(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                monthly_fee=str(value),
            )

        if source_step == TelegramStep.WAITING_STUDENT_DUE_DAY:
            return await self._apply_confirmed_student_due_day(
                chat_id=chat_id,
                state_id=state_id,
                context_data=updated_context_data,
                due_day=int(value),
            )

        await self.send_menu(chat_id)

        return {'status': 'student_field_confirmation_invalid_source'}

    @staticmethod
    def _build_field_confirmation_text(
        field_label: str,
        display_value: str,
    ) -> str:
        return (
            f'Confirme {field_label}:\n\n'
            f'{display_value}\n\n'
            'Escolha uma opção abaixo.'
        )

    @staticmethod
    def _get_pending_source_step(
        pending_field_confirmation: dict[str, Any],
    ) -> TelegramStep | None:
        source_step = pending_field_confirmation.get('source_step')

        try:
            return TelegramStep(str(source_step))
        except ValueError:
            return None

    @staticmethod
    def _get_waiting_status_for_step(
        step: TelegramStep,
    ) -> str:
        waiting_statuses = {
            TelegramStep.WAITING_STUDENT_NAME: 'waiting_student_name',
            TelegramStep.WAITING_STUDENT_PHONE: 'waiting_student_phone',
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_NAME: (
                'waiting_student_responsible_name'
            ),
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_PHONE: (
                'waiting_student_responsible_phone'
            ),
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_EMAIL: (
                'waiting_student_responsible_email'
            ),
            TelegramStep.WAITING_STUDENT_ADDRESS_ZIP_CODE: (
                'waiting_student_address_zip_code'
            ),
            TelegramStep.WAITING_STUDENT_ADDRESS_STREET: (
                'waiting_student_address_street'
            ),
            TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD: (
                'waiting_student_address_neighborhood'
            ),
            TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER: (
                'waiting_student_address_number'
            ),
            TelegramStep.WAITING_STUDENT_ADDRESS_COMPLEMENT: (
                'waiting_student_address_complement'
            ),
            TelegramStep.WAITING_STUDENT_CPF: 'waiting_student_cpf',
            TelegramStep.WAITING_STUDENT_INSTAGRAM: (
                'waiting_student_instagram'
            ),
            TelegramStep.WAITING_STUDENT_EMAIL: 'waiting_student_email',
            TelegramStep.WAITING_STUDENT_BIRTH_DATE: (
                'waiting_student_birth_date'
            ),
            TelegramStep.WAITING_STUDENT_MONTHLY_FEE: (
                'waiting_student_monthly_fee'
            ),
            TelegramStep.WAITING_STUDENT_DUE_DAY: 'waiting_student_due_day',
        }

        return waiting_statuses.get(step, 'waiting_student_field')

    @staticmethod
    def _clear_address_context(
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        updated_context_data = dict(context_data)

        for key in (
            'address',
            'address_reference',
            'address_reference_student_id',
            'address_reference_student_name',
        ):
            updated_context_data.pop(key, None)

        return updated_context_data

    async def process_student_name_message(
        self,
        chat_id: int,
        student_name: str,
        state_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_student_name = ' '.join(student_name.strip().split())

        if len(normalized_student_name) < MIN_STUDENT_NAME_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'O nome do aluno precisa ter pelo menos 2 caracteres.\n\n'
                    'Digite o nome completo do aluno novamente.'
                ),
            )

            return {'status': 'invalid_student_name'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data={},
            source_step=TelegramStep.WAITING_STUDENT_NAME,
            field_label='o nome do aluno',
            value=normalized_student_name,
            display_value=normalized_student_name,
            prompt_text=(
                '➕ Cadastrar novo aluno\n\n'
                'Vamos cadastrar um novo aluno na sua academia.\n\n'
                'Digite o nome completo do aluno.'
            ),
            prompt_reply_markup=student_creation_cancel_reply_markup(),
        )

    async def _apply_confirmed_student_name(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
        student_name: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['student_name'] = student_name

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_MODALITY,
            context_data=updated_context_data,
        )

        modalities = await self.modality_service.list_selected_by_academy(
            context.academy_id
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Perfeito! ✅\n\n'
                f'Aluno: {student_name}\n\n'
                'Agora escolha a modalidade do aluno:'
            ),
            reply_markup=student_modalities_reply_markup(modalities),
        )

        return {'status': 'waiting_student_modality'}

    async def process_student_address_reference_search_message(
        self,
        chat_id: int,
        search_text: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_search_text = ' '.join(search_text.strip().split())

        if len(normalized_search_text) < MIN_STUDENT_NAME_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Digite pelo menos 2 caracteres para pesquisar.\n\n'
                    'Exemplo:\n'
                    'João'
                ),
            )

            return {'status': 'invalid_student_address_reference_search_text'}

        students = await self.student_service.search_by_name(
            academy_id=context.academy_id,
            search_text=normalized_search_text,
        )

        if not students:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei nenhum aluno com o nome '
                    f'"{normalized_search_text}".\n\n'
                    'O que deseja fazer?'
                ),
                reply_markup={
                    'inline_keyboard': (
                        student_address_reference_search_actions_rows()
                    ),
                },
            )

            return {'status': 'student_address_reference_search_empty'}

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
            context_data=context_data,
        )

        inline_keyboard: list[list[dict[str, str]]] = []

        for student in students:
            inline_keyboard.append([
                {
                    'text': f'🏠 {student.name}',
                    'callback_data': (
                        f'students:create:address:reference:{student.id}'
                    ),
                },
            ])

        inline_keyboard.extend(
            student_address_reference_search_actions_rows(),
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Encontrei estes alunos.\n\n'
                'Toque no aluno que possui o endereço que deseja reutilizar.'
            ),
            reply_markup={'inline_keyboard': inline_keyboard},
        )

        return {'status': 'student_address_reference_search_sent'}

    async def _start_student_creation(
        self,
        chat_id: int,
        telegram_user_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.start_student_creation(
            telegram_user_id=telegram_user_id,
            academy_id=context.academy_id,
            master_id=context.master_id,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '➕ Cadastrar novo aluno\n\n'
                'Vamos cadastrar um novo aluno na sua academia.\n\n'
                'Digite o nome completo do aluno.'
            ),
            reply_markup=student_creation_cancel_reply_markup(),
        )

        return {'status': 'student_creation_started'}

    async def _process_modality_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        modality_id = self._get_modality_id_from_callback(callback_data)

        if modality_id is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_modality'}

        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_modality(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro de aluno em andamento.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_creation_state_not_found'}

        selected_modality = await self._get_selected_modality(
            academy_id=context.academy_id,
            modality_id=modality_id,
        )

        if selected_modality is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Essa modalidade não está configurada na sua academia.\n\n'
                    'Escolha uma modalidade válida.'
                ),
            )

            return {'status': 'invalid_academy_modality'}

        context_data = dict(state['context_data'])
        context_data['modality_id'] = selected_modality.id
        context_data['modality_name'] = selected_modality.name

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_SEX,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=f'Modalidade selecionada: {selected_modality.name} ✅',
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Agora escolha o sexo do aluno:',
            reply_markup=student_sex_reply_markup(),
        )

        return {'status': 'waiting_student_sex'}

    async def process_student_phone_message(
        self,
        chat_id: int,
        phone: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_phone = ''.join(
            character for character in phone if character.isdigit()
        )

        if not (MIN_PHONE_LENGTH <= len(normalized_phone) <= MAX_PHONE_LENGTH):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Telefone inválido.\n\n'
                    'Digite apenas os números, com DDD.\n\n'
                    'Exemplo:\n'
                    '62999999999'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'invalid_student_phone'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_PHONE,
            field_label='o telefone do aluno',
            value=normalized_phone,
            display_value=normalized_phone,
            prompt_text=(
                'Qual é o telefone do aluno?\n\n'
                'Digite apenas os números, com DDD.\n\n'
                'Exemplo:\n'
                '62999999999\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_phone(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        phone: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['phone'] = phone

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_IS_WHATSAPP,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Esse telefone é WhatsApp?',
            reply_markup=yes_no_skip_reply_markup(
                yes_callback_data='students:create:whatsapp:yes',
                no_callback_data='students:create:whatsapp:no',
            ),
        )

        return {'status': 'waiting_student_is_whatsapp'}

    async def _process_sex_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        sex_options = {
            'students:create:sex:male': 'masculino',
            'students:create:sex:female': 'feminino',
            'students:create:sex:other': 'outros',
        }
        selected_sex = sex_options.get(callback_data)

        if selected_sex is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_sex'}

        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_sex(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro de aluno aguardando sexo.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_sex_state_not_found'}

        context_data = dict(state['context_data'])
        context_data['sex'] = selected_sex

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_TYPE,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=f'Sexo selecionado: {selected_sex.capitalize()} ✅',
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Esse aluno é o próprio responsável?',
            reply_markup=student_responsible_type_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_type'}

    async def _process_responsible_type_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_responsible_type(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando responsável.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_responsible_type_state_not_found'}

        context_data = dict(state['context_data'])

        if callback_data == 'students:create:responsible:self':
            context_data['responsible_type'] = 'self'

            await state_service.update_student_creation_context(
                state_id=state['id'],
                next_step=TelegramStep.WAITING_STUDENT_PHONE,
                context_data=context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Qual é o telefone do aluno?\n\n'
                    'Digite apenas os números, com DDD.\n\n'
                    'Exemplo:\n'
                    '62999999999\n\n'
                    'Se não quiser informar agora, toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_phone'}

        context_data['responsible_type'] = 'external'
        context_data.setdefault('responsibles', [])
        context_data.setdefault('responsible_references', [])

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_CHOICE,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Como deseja informar o responsável do aluno?',
            reply_markup=student_responsible_choice_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_choice'}

    async def _process_responsible_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        valid_steps = {
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_CHOICE,
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_NEXT_ACTION,
            TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH,
        }

        if state is None or state['current_step'] not in valid_steps:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando escolha '
                    'de responsável.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_responsible_choice_state_not_found'}

        context_data = dict(state['context_data'])

        if callback_data == RESPONSIBLE_BACK_CALLBACK_DATA:
            await state_service.update_student_creation_context(
                state_id=state['id'],
                next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_CHOICE,
                context_data=context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Como deseja informar o responsável do aluno?',
                reply_markup=student_responsible_choice_reply_markup(),
            )

            return {'status': 'waiting_student_responsible_choice'}

        if callback_data == 'students:create:responsible:new':
            await state_service.update_student_creation_context(
                state_id=state['id'],
                next_step=(
                    TelegramStep.WAITING_STUDENT_RESPONSIBLE_RELATIONSHIP
                ),
                context_data=context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    '👨‍👩‍👧 Responsável\n\n'
                    'Qual é o parentesco do responsável com o aluno?'
                ),
                reply_markup=student_responsible_relationship_reply_markup(),
            )

            return {'status': 'waiting_student_responsible_relationship'}

        return await self._prompt_student_responsible_reference_search(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
        )

    async def process_student_responsible_reference_search_message(
        self,
        chat_id: int,
        search_text: str,
        state_id: int,
        context_data: dict[str, Any],
        context: MasterContextRead,
    ) -> dict[str, str]:
        normalized_search_text = ' '.join(search_text.strip().split())

        if len(normalized_search_text) < MIN_STUDENT_NAME_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Digite pelo menos 2 caracteres para pesquisar.\n\n'
                    'Exemplo:\n'
                    'João'
                ),
            )

            return {
                'status': 'invalid_student_responsible_reference_search_text'
            }

        students = await self.student_service.search_by_name(
            academy_id=context.academy_id,
            search_text=normalized_search_text,
        )

        if not students:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei nenhum aluno com o nome '
                    f'"{normalized_search_text}".\n\n'
                    'O que deseja fazer?'
                ),
                reply_markup={
                    'inline_keyboard': (
                        student_responsible_reference_search_actions_rows()
                    ),
                },
            )

            return {'status': 'student_responsible_reference_search_empty'}

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH,
            context_data=context_data,
        )

        inline_keyboard: list[list[dict[str, str]]] = []

        for student in students:
            inline_keyboard.append([
                {
                    'text': f'🔁 {student.name}',
                    'callback_data': (
                        f'students:create:responsible:reference:{student.id}'
                    ),
                },
            ])

        inline_keyboard.extend(
            student_responsible_reference_search_actions_rows(),
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Encontrei estes alunos.\n\n'
                'Toque no aluno que já possui o mesmo responsável.'
            ),
            reply_markup={'inline_keyboard': inline_keyboard},
        )

        return {'status': 'student_responsible_reference_search_sent'}

    async def _process_responsible_reference_selected(
        self,
        chat_id: int,
        telegram_user_id: int,
        context: MasterContextRead,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if (
            state is None
            or state['current_step']
            != TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH
        ):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando escolha '
                    'de responsável.'
                ),
            )

            return {'status': 'student_responsible_reference_state_not_found'}

        reference_student_id = self._get_id_from_callback(callback_data)

        if reference_student_id is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Aluno inválido. Digite novamente o nome do aluno.',
            )

            return {'status': 'student_responsible_reference_invalid_id'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=reference_student_id,
        )

        if details is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei esse aluno. Digite outro nome para buscar.'
                ),
            )

            return {'status': 'student_responsible_reference_not_found'}

        responsibles = details.get('responsibles', [])

        if not responsibles:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Esse aluno não possui responsável cadastrado.\n\n'
                    'O que deseja fazer?'
                ),
                reply_markup={
                    'inline_keyboard': (
                        student_responsible_reference_search_actions_rows()
                    ),
                },
            )

            return {'status': 'student_responsible_reference_without_data'}

        reference_student = details['student']
        inline_keyboard = self._build_responsible_reference_keyboard(
            student_id=reference_student_id,
            responsibles=responsibles,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                f'Aluno referência: {reference_student["name"]}\n\n'
                'Quais responsáveis deseja reutilizar?'
            ),
            reply_markup={'inline_keyboard': inline_keyboard},
        )

        return {'status': 'student_responsible_reference_options_sent'}

    async def _process_responsible_reference_all_selected(
        self,
        chat_id: int,
        telegram_user_id: int,
        context: MasterContextRead,
        callback_data: str,
    ) -> dict[str, str]:
        reference_student_id = self._get_id_from_callback(callback_data)

        if reference_student_id is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Aluno inválido. Digite novamente o nome do aluno.',
            )

            return {'status': 'student_responsible_reference_invalid_id'}

        return await self._save_responsible_references(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            context=context,
            reference_student_id=reference_student_id,
            selected_responsible_id=None,
        )

    async def _process_responsible_reference_one_selected(
        self,
        chat_id: int,
        telegram_user_id: int,
        context: MasterContextRead,
        callback_data: str,
    ) -> dict[str, str]:
        ids = callback_data.rsplit(':', maxsplit=2)

        if (
            len(ids) != RESPONSIBLE_REFERENCE_CALLBACK_PARTS
            or not ids[-2].isdigit()
            or not ids[-1].isdigit()
        ):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Responsável inválido. Digite novamente o nome do aluno.',
            )

            return {'status': 'student_responsible_reference_invalid_id'}

        return await self._save_responsible_references(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            context=context,
            reference_student_id=int(ids[-2]),
            selected_responsible_id=int(ids[-1]),
        )

    async def _save_responsible_references(
        self,
        chat_id: int,
        telegram_user_id: int,
        context: MasterContextRead,
        reference_student_id: int,
        selected_responsible_id: int | None,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if (
            state is None
            or state['current_flow'] != TelegramFlow.STUDENT_CREATION
        ):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro de aluno em andamento.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_responsible_reference_state_not_found'}

        details = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=reference_student_id,
        )

        if details is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei esse aluno. Digite outro nome para buscar.'
                ),
            )

            return {'status': 'student_responsible_reference_not_found'}

        responsibles = details.get('responsibles', [])

        if selected_responsible_id is not None:
            responsibles = [
                responsible
                for responsible in responsibles
                if self._get_responsible_id(responsible)
                == selected_responsible_id
            ]

        if not responsibles:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei responsável para reaproveitar.\n\n'
                    'O que deseja fazer?'
                ),
                reply_markup={
                    'inline_keyboard': (
                        student_responsible_reference_search_actions_rows()
                    ),
                },
            )

            return {'status': 'student_responsible_reference_without_data'}

        context_data = dict(state['context_data'])
        responsible_references = list(
            context_data.get('responsible_references', [])
        )
        responsible_reference_details = list(
            context_data.get('responsible_reference_details', [])
        )

        for responsible in responsibles:
            responsible_id = self._get_responsible_id(responsible)

            if responsible_id is None:
                continue

            responsible_references.append({
                'responsible_id': responsible_id,
                'relationship': responsible['relationship'],
            })
            responsible_reference_details.append({
                'responsible_id': responsible_id,
                'relationship': responsible['relationship'],
                'name': responsible['name'],
                'phone': responsible['phone'],
                'phone_is_whatsapp': responsible.get('phone_is_whatsapp'),
                'email': responsible.get('email'),
            })

        context_data['responsible_references'] = responsible_references
        context_data['responsible_reference_details'] = (
            responsible_reference_details
        )
        context_data['responsible_reference_student_name'] = details[
            'student'
        ]['name']

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_NEXT_ACTION,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Responsável reaproveitado com sucesso! ✅\n\n'
                'Deseja cadastrar mais um responsável ou continuar '
                'o cadastro do aluno?'
            ),
            reply_markup=student_responsible_next_action_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_next_action'}

    @staticmethod
    def _build_responsible_reference_keyboard(
        student_id: int,
        responsibles: list[dict[str, Any]],
    ) -> list[list[dict[str, str]]]:
        inline_keyboard = [
            [
                {
                    'text': '🔁 Usar todos os responsáveis',
                    'callback_data': (
                        'students:create:responsible:reference_all:'
                        f'{student_id}'
                    ),
                },
            ],
        ]

        for responsible in responsibles:
            responsible_id = StudentsMenuHandler._get_responsible_id(
                responsible,
            )

            if responsible_id is None:
                continue

            relationship = StudentsMenuHandler._get_relationship_label(
                responsible['relationship'],
            )

            inline_keyboard.append([
                {
                    'text': f'{relationship}: {responsible["name"]}',
                    'callback_data': (
                        'students:create:responsible:reference_one:'
                        f'{student_id}:{responsible_id}'
                    ),
                },
            ])

        inline_keyboard.append([
            {
                'text': '❌ Cancelar cadastro',
                'callback_data': 'students:create:cancel',
            },
        ])

        return inline_keyboard

    @staticmethod
    def _get_responsible_id(
        responsible: dict[str, Any],
    ) -> int | None:
        responsible_id = responsible.get('responsible_id')

        if responsible_id is None:
            responsible_id = responsible.get('id')

        if responsible_id is None:
            return None

        return int(responsible_id)

    @staticmethod
    def _get_id_from_callback(
        callback_data: str,
    ) -> int | None:
        raw_id = callback_data.rsplit(':', maxsplit=1)[-1]

        if not raw_id.isdigit():
            return None

        return int(raw_id)

    async def _process_responsible_relationship_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_responsible_relationship(state):
            if self._is_waiting_student_responsible_name(state):
                await self.telegram_service.send_message(
                    chat_id=chat_id,
                    text='Qual é o nome do responsável?',
                )

                return {'status': 'waiting_student_responsible_name'}

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando parentesco.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {
                'status': 'student_responsible_relationship_state_not_found'
            }

        relationship = callback_data.removeprefix(
            'students:create:responsible:relationship:'
        )

        context_data = dict(state['context_data'])
        context_data['current_responsible'] = {
            'relationship': relationship,
        }

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_NAME,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '👨‍👩‍👧 Responsável\n\nDigite o nome completo do responsável.'
            ),
            reply_markup=student_creation_cancel_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_name'}

    async def process_student_responsible_name_message(
        self,
        chat_id: int,
        responsible_name: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_responsible_name = ' '.join(
            responsible_name.strip().split()
        )

        if len(normalized_responsible_name) < MIN_STUDENT_NAME_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'O nome do responsável precisa ter pelo menos '
                    '2 caracteres.\n\n'
                    'Digite o nome do responsável novamente.'
                ),
            )

            return {'status': 'invalid_student_responsible_name'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_NAME,
            field_label='o nome do responsável',
            value=normalized_responsible_name,
            display_value=normalized_responsible_name,
            prompt_text='Qual é o nome do responsável?',
            prompt_reply_markup=student_creation_cancel_reply_markup(),
        )

    async def _apply_confirmed_student_responsible_name(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        responsible_name: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        current_responsible = dict(updated_context_data['current_responsible'])
        current_responsible['name'] = responsible_name
        updated_context_data['current_responsible'] = current_responsible

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_PHONE,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o telefone do responsável?\n\n'
                'Digite apenas os números, com DDD.\n\n'
                'Exemplo:\n'
                '62999999999'
            ),
            reply_markup=student_creation_cancel_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_phone'}

    async def process_student_responsible_phone_message(
        self,
        chat_id: int,
        phone: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_phone = ''.join(
            character for character in phone if character.isdigit()
        )

        if not (MIN_PHONE_LENGTH <= len(normalized_phone) <= MAX_PHONE_LENGTH):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Telefone inválido.\n\n'
                    'Digite apenas os números, com DDD.\n\n'
                    'Exemplo:\n'
                    '62999999999'
                ),
            )

            return {'status': 'invalid_student_responsible_phone'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_PHONE,
            field_label='o telefone do responsável',
            value=normalized_phone,
            display_value=normalized_phone,
            prompt_text=(
                'Qual é o telefone do responsável?\n\n'
                'Digite apenas os números, com DDD.\n\n'
                'Exemplo:\n'
                '62999999999'
            ),
            prompt_reply_markup=student_creation_cancel_reply_markup(),
        )

    async def _apply_confirmed_student_responsible_phone(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        phone: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        current_responsible = dict(updated_context_data['current_responsible'])
        current_responsible['phone'] = phone
        updated_context_data['current_responsible'] = current_responsible

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_IS_WHATSAPP,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Esse telefone é WhatsApp?',
            reply_markup=yes_no_required_reply_markup(
                yes_callback_data=('students:create:responsible:whatsapp:yes'),
                no_callback_data='students:create:responsible:whatsapp:no',
            ),
        )

        return {'status': 'waiting_student_responsible_is_whatsapp'}

    async def _process_responsible_whatsapp_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        whatsapp_options = {
            'students:create:responsible:whatsapp:yes': True,
            'students:create:responsible:whatsapp:no': False,
        }
        is_whatsapp = whatsapp_options.get(callback_data)

        if is_whatsapp is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_responsible_whatsapp'}

        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_responsible_is_whatsapp(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando WhatsApp '
                    'do responsável.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_responsible_whatsapp_state_not_found'}

        context_data = dict(state['context_data'])
        current_responsible = dict(context_data['current_responsible'])
        current_responsible['phone_is_whatsapp'] = is_whatsapp
        context_data['current_responsible'] = current_responsible

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_EMAIL,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o e-mail do responsável?\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_email'}

    async def _process_responsible_next_action_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_responsible_next_action(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando próxima ação.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {
                'status': 'student_responsible_next_action_state_not_found'
            }

        context_data = dict(state['context_data'])

        if callback_data == 'students:create:responsible:add':
            await state_service.update_student_creation_context(
                state_id=state['id'],
                next_step=(
                    TelegramStep.WAITING_STUDENT_RESPONSIBLE_RELATIONSHIP
                ),
                context_data=context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    '👨‍👩‍👧 Responsável\n\n'
                    'Qual é o parentesco do responsável com o aluno?'
                ),
                reply_markup=student_responsible_relationship_reply_markup(),
            )

            return {'status': 'waiting_student_responsible_relationship'}

        return await self._ask_student_address_choice(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
        )

    async def _process_address_change_zip(
        self,
        chat_id: int,
        telegram_user_id: int,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if (
            state is None
            or state['current_step']
            != TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER
        ):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando número '
                    'de endereço.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar '
                    'novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_address_change_zip_state_not_found'}

        context_data = dict(state['context_data'])
        context_data.pop('address', None)

        return await self._ask_student_address_zip_code(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
        )

    async def _process_address_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        valid_steps = {
            TelegramStep.WAITING_STUDENT_ADDRESS_CHOICE,
            TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
        }

        if state is None or state['current_step'] not in valid_steps:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando escolha '
                    'de endereço.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar '
                    'novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_address_choice_state_not_found'}

        context_data = dict(state['context_data'])

        if callback_data == 'students:create:address:new':
            context_data = self._clear_address_context(context_data)

            return await self._ask_student_address_zip_code(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data == ADDRESS_BACK_CALLBACK_DATA:
            context_data = self._clear_address_context(context_data)

            return await self._ask_student_address_choice(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if callback_data == 'students:create:address:skip':
            context_data = self._clear_address_context(context_data)

            return await self._skip_to_cpf(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        context_data = self._clear_address_context(context_data)

        return await self._prompt_student_address_reference_search(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
        )

    async def _process_address_reference_selected(
        self,
        chat_id: int,
        telegram_user_id: int,
        context: MasterContextRead,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if (
            state is None
            or state['current_flow'] != TelegramFlow.STUDENT_CREATION
        ):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro de aluno em andamento.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_address_reference_state_not_found'}

        reference_student_id_text = callback_data.rsplit(':', maxsplit=1)[-1]

        if not reference_student_id_text.isdigit():
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text='Aluno inválido. Digite novamente o nome do aluno.',
            )

            return {'status': 'student_address_reference_invalid_id'}

        reference_student_id = int(reference_student_id_text)

        reference_student = await self.student_service.get_details(
            academy_id=context.academy_id,
            student_id=reference_student_id,
        )

        if reference_student is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei esse aluno. Digite outro nome para buscar.'
                ),
            )

            return {'status': 'student_address_reference_not_found'}

        address_reference = reference_student.get('address')

        if not isinstance(address_reference, dict):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Esse aluno não possui endereço cadastrado.\n\n'
                    'O que deseja fazer?'
                ),
                reply_markup={
                    'inline_keyboard': (
                        student_address_reference_search_actions_rows()
                    ),
                },
            )

            return {'status': 'student_address_reference_without_data'}

        context_data = self._clear_address_context(state['context_data'])
        context_data['address_reference_student_id'] = reference_student_id
        context_data['address_reference_student_name'] = reference_student[
            'student'
        ]['name']
        context_data['address_reference'] = {
            'zip_code': address_reference.get('zip_code'),
            'street': address_reference.get('street'),
            'number': address_reference.get('number'),
            'complement': address_reference.get('complement'),
            'neighborhood': address_reference.get('neighborhood'),
            'city': address_reference.get('city'),
            'state': address_reference.get('state'),
        }

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_CPF,
            context_data=context_data,
        )

        reference_student_name = reference_student['student']['name']

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                f'✅ Endereço reaproveitado de {reference_student_name}.\n\n'
                'Agora vamos continuar o cadastro.'
            ),
        )

        return await self._skip_to_cpf(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
        )

    async def process_student_address_zip_code_message(
        self,
        chat_id: int,
        zip_code: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_zip_code = ''.join(
            character for character in zip_code if character.isdigit()
        )

        if len(normalized_zip_code) != ZIP_CODE_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'CEP inválido.\n\n'
                    'Digite apenas os 8 números do CEP.\n\n'
                    'Exemplo:\n'
                    '74230110\n\n'
                    'Se não quiser informar agora, toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'invalid_student_address_zip_code'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_ADDRESS_ZIP_CODE,
            field_label='o CEP do aluno',
            value=normalized_zip_code,
            display_value=normalized_zip_code,
            prompt_text=(
                'Qual é o CEP do aluno?\n\n'
                'Digite apenas os números.\n\n'
                'Exemplo:\n'
                '74230110\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_address_zip_code(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        zip_code: str,
    ) -> dict[str, str]:
        cep_address = await self.cep_service.search(zip_code)

        if cep_address is None:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei esse CEP.\n\n'
                    'Você pode tentar digitar outro CEP ou tocar em '
                    '"⏭️ Pular" para continuar sem endereço agora.'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'student_address_zip_code_not_found'}

        updated_context_data = dict(context_data)
        updated_context_data['address'] = {
            'zip_code': cep_address.zip_code,
            'street': cep_address.street,
            'neighborhood': cep_address.neighborhood,
            'city': cep_address.city,
            'state': cep_address.state,
        }

        state_service = self.telegram_conversation_state_service

        if not cep_address.street:
            await state_service.update_student_creation_context(
                state_id=state_id,
                next_step=TelegramStep.WAITING_STUDENT_ADDRESS_STREET,
                context_data=updated_context_data,
            )

            missing_fields_text = 'o logradouro'

            if not cep_address.neighborhood:
                missing_fields_text = 'logradouro nem bairro'

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Encontrei parcialmente este endereço:\n\n'
                    f'Cidade/Estado: {cep_address.city}/{cep_address.state}\n'
                    f'CEP: {cep_address.zip_code}\n\n'
                    f'O CEP não trouxe {missing_fields_text}.\n\n'
                    'Primeiro, digite o logradouro ou toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_address_street'}

        if not cep_address.neighborhood:
            await state_service.update_student_creation_context(
                state_id=state_id,
                next_step=(TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD),
                context_data=updated_context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Encontrei parcialmente este endereço:\n\n'
                    f'Logradouro: {cep_address.street}\n'
                    f'Cidade/Estado: {cep_address.city}/{cep_address.state}\n'
                    f'CEP: {cep_address.zip_code}\n\n'
                    'O CEP não trouxe o bairro.\n\n'
                    'Digite o bairro ou toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_address_neighborhood'}

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Encontrei este endereço:\n\n'
                f'Logradouro: {cep_address.street}\n'
                f'Bairro: {cep_address.neighborhood}\n'
                f'Cidade/Estado: {cep_address.city}/{cep_address.state}\n'
                f'CEP: {cep_address.zip_code}\n\n'
                'Agora digite o número do endereço.\n\n'
                'Exemplos:\n'
                '123\n'
                '3B\n'
                'S/N'
            ),
            reply_markup=student_address_number_reply_markup(),
        )

        return {'status': 'waiting_student_address_number'}

    async def process_student_address_street_message(
        self,
        chat_id: int,
        street: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_street = ' '.join(street.strip().split())

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_ADDRESS_STREET,
            field_label='o logradouro do endereço',
            value=normalized_street,
            display_value=normalized_street,
            prompt_text=(
                'Digite o logradouro do endereço.\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_address_street(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        street: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('address', {}))
        address['street'] = street
        updated_context_data['address'] = address

        state_service = self.telegram_conversation_state_service

        if not address.get('neighborhood'):
            await state_service.update_student_creation_context(
                state_id=state_id,
                next_step=(TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD),
                context_data=updated_context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Agora digite o bairro do endereço.\n\n'
                    'Se não quiser informar agora, toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_address_neighborhood'}

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Agora digite o número do endereço.\n\nExemplos:\n123\n3B\nS/N'
            ),
        )

        return {'status': 'waiting_student_address_number'}

    async def process_student_address_neighborhood_message(
        self,
        chat_id: int,
        neighborhood: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_neighborhood = ' '.join(neighborhood.strip().split())

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD,
            field_label='o bairro do endereço',
            value=normalized_neighborhood,
            display_value=normalized_neighborhood,
            prompt_text=(
                'Digite o bairro do endereço.\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_address_neighborhood(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        neighborhood: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('address', {}))
        address['neighborhood'] = neighborhood
        updated_context_data['address'] = address

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Agora digite o número do endereço.\n\nExemplos:\n123\n3B\nS/N'
            ),
        )

        return {'status': 'waiting_student_address_number'}

    async def process_student_address_number_message(
        self,
        chat_id: int,
        number: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_number = ' '.join(number.strip().split())
        normalized_number_compact = normalized_number.casefold().replace(
            ' ',
            '',
        )

        no_number_values = {'s/n', 'sn', 'semnumero', 'semnúmero'}

        if normalized_number_compact in no_number_values:
            normalized_number = 'S/N'

        if not normalized_number:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Número inválido.\n\n'
                    'Digite o número do endereço.\n\n'
                    'Exemplos:\n'
                    '123\n'
                    '3B\n'
                    'S/N'
                ),
                reply_markup=student_address_number_reply_markup(),
            )

            return {'status': 'invalid_student_address_number'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER,
            field_label='o número do endereço',
            value=normalized_number,
            display_value=normalized_number,
            prompt_text=(
                'Digite o número do endereço.\n\nExemplos:\n123\n3B\nS/N'
            ),
            prompt_reply_markup=student_address_number_reply_markup(),
        )

    async def _apply_confirmed_student_address_number(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        number: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('address', {}))
        address['number'] = number
        updated_context_data['address'] = address

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_COMPLEMENT,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Digite o complemento do endereço.\n\n'
                'Exemplo:\n'
                'Casa 2\n\n'
                'Se não tiver complemento, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_address_complement'}

    async def process_student_address_complement_message(
        self,
        chat_id: int,
        complement: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_complement = complement.strip()

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_ADDRESS_COMPLEMENT,
            field_label='o complemento do endereço',
            value=normalized_complement,
            display_value=normalized_complement or 'Sem complemento',
            prompt_text=(
                'Digite o complemento do endereço.\n\n'
                'Exemplo:\n'
                'Casa 2\n\n'
                'Se não tiver complemento, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_address_complement(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        complement: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        address = dict(updated_context_data.get('address', {}))
        address['complement'] = complement
        updated_context_data['address'] = address

        return await self._skip_to_cpf(
            chat_id=chat_id,
            state_id=state_id,
            context_data=updated_context_data,
        )

    async def process_student_cpf_message(
        self,
        chat_id: int,
        cpf: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_cpf = ''.join(
            character for character in cpf if character.isdigit()
        )

        if len(normalized_cpf) != CPF_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'CPF inválido.\n\n'
                    'Digite apenas os números, sem pontos ou traços.\n\n'
                    'Exemplo:\n'
                    '12345678911'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'invalid_student_cpf'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_CPF,
            field_label='o CPF do aluno',
            value=normalized_cpf,
            display_value=normalized_cpf,
            prompt_text=(
                'Qual é o CPF do aluno?\n\n'
                'Digite apenas os números, sem pontos ou traços.\n\n'
                'Exemplo:\n'
                '12345678911\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_cpf(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        cpf: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['cpf'] = cpf

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_INSTAGRAM,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o Instagram do aluno?\n\n'
                'Digite sem @.\n\n'
                'Exemplo:\n'
                'joaosilva\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_instagram'}

    async def process_student_instagram_message(
        self,
        chat_id: int,
        instagram: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_instagram = instagram.strip().removeprefix('@').casefold()

        if len(normalized_instagram) < MIN_INSTAGRAM_LENGTH:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Instagram inválido.\n\n'
                    'Digite sem @.\n\n'
                    'Exemplo:\n'
                    'joaosilva'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'invalid_student_instagram'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_INSTAGRAM,
            field_label='o Instagram do aluno',
            value=normalized_instagram,
            display_value=f'@{normalized_instagram}',
            prompt_text=(
                'Qual é o Instagram do aluno?\n\n'
                'Digite sem @.\n\n'
                'Exemplo:\n'
                'joaosilva\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_instagram(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        instagram: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['instagram'] = instagram

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_EMAIL,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o e-mail do aluno?\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_email'}

    async def process_student_email_message(
        self,
        chat_id: int,
        email: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_email = email.strip().casefold().casefold().lower()

        if not self._is_valid_email(normalized_email):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'E-mail inválido.\n\n'
                    'Digite um e-mail válido ou toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'invalid_student_email'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_EMAIL,
            field_label='o e-mail do aluno',
            value=normalized_email,
            display_value=normalized_email,
            prompt_text=(
                'Qual é o e-mail do aluno?\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_email(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        email: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['email'] = email

        return await self._skip_to_birth_date(
            chat_id=chat_id,
            state_id=state_id,
            context_data=updated_context_data,
        )

    async def process_student_responsible_email_message(
        self,
        chat_id: int,
        email: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        normalized_email = email.strip().lower()

        if not self._is_valid_email(normalized_email):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'E-mail inválido.\n\n'
                    'Digite um e-mail válido ou toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'invalid_student_responsible_email'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_EMAIL,
            field_label='o e-mail do responsável',
            value=normalized_email,
            display_value=normalized_email,
            prompt_text=(
                'Qual é o e-mail do responsável?\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_responsible_email(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        email: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        current_responsible = dict(updated_context_data['current_responsible'])
        current_responsible['email'] = email
        updated_context_data['current_responsible'] = current_responsible

        return await self._finish_current_responsible(
            chat_id=chat_id,
            state_id=state_id,
            context_data=updated_context_data,
        )

    async def _finish_current_responsible(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        current_responsible = dict(updated_context_data['current_responsible'])

        responsibles = list(updated_context_data.get('responsibles', []))
        responsibles.append(current_responsible)

        updated_context_data['responsibles'] = responsibles
        updated_context_data.pop('current_responsible', None)

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_NEXT_ACTION,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Responsável cadastrado com sucesso! ✅\n\n'
                'Deseja cadastrar mais um responsável ou continuar '
                'o cadastro do aluno?'
            ),
            reply_markup=student_responsible_next_action_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_next_action'}

    async def process_student_birth_date_message(
        self,
        chat_id: int,
        birth_date_text: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        try:
            birth_date = datetime.strptime(
                birth_date_text.strip(),
                BIRTH_DATE_FORMAT,
            ).date()
        except ValueError:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Data de nascimento inválida.\n\n'
                    'Digite no formato dia/mês/ano.\n\n'
                    'Exemplo:\n'
                    '24/01/1994'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'invalid_student_birth_date'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_BIRTH_DATE,
            field_label='a data de nascimento do aluno',
            value=birth_date.isoformat(),
            display_value=birth_date.strftime(BIRTH_DATE_FORMAT),
            prompt_text=(
                'Qual é a data de nascimento do aluno?\n\n'
                'Digite no formato dia/mês/ano.\n\n'
                'Exemplo:\n'
                '24/01/1994\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            prompt_reply_markup=optional_field_reply_markup(),
        )

    async def _apply_confirmed_student_birth_date(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        birth_date: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['birth_date'] = birth_date

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_MONTHLY_FEE,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o valor da mensalidade do aluno?\n\n'
                'Exemplo:\n'
                '125\n'
                'ou\n'
                '100,50'
            ),
        )

        return {'status': 'waiting_student_monthly_fee'}

    async def process_student_monthly_fee_message(
        self,
        chat_id: int,
        monthly_fee_text: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        monthly_fee = self._parse_monthly_fee(monthly_fee_text)

        if monthly_fee is None:
            await self._send_invalid_monthly_fee_message(chat_id)

            return {'status': 'invalid_student_monthly_fee'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_MONTHLY_FEE,
            field_label='o valor da mensalidade',
            value=str(monthly_fee),
            display_value=f'R$ {monthly_fee}',
            prompt_text=(
                'Qual é o valor da mensalidade do aluno?\n\n'
                'Exemplo:\n'
                '125\n'
                'ou\n'
                '100,50'
            ),
        )

    async def _apply_confirmed_student_monthly_fee(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        monthly_fee: str,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['monthly_fee'] = monthly_fee

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_DUE_DAY,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o dia de vencimento da mensalidade?\n\n'
                'Digite um dia entre 1 e 28.\n\n'
                'Exemplo:\n'
                '10'
            ),
        )

        return {'status': 'waiting_student_due_day'}

    async def _send_invalid_monthly_fee_message(
        self,
        chat_id: int,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Valor de mensalidade inválido.\n\n'
                'Digite apenas o valor.\n\n'
                'Exemplo:\n'
                '125\n'
                'ou\n'
                '100,50'
            ),
        )

    async def process_student_due_day_message(
        self,
        chat_id: int,
        due_day_text: str,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        due_day = self._parse_due_day(due_day_text)

        if due_day is None:
            await self._send_invalid_due_day_message(chat_id)

            return {'status': 'invalid_student_due_day'}

        return await self._request_field_confirmation(
            chat_id=chat_id,
            state_id=state_id,
            context_data=context_data,
            source_step=TelegramStep.WAITING_STUDENT_DUE_DAY,
            field_label='o dia de vencimento',
            value=due_day,
            display_value=f'Dia {due_day}',
            prompt_text=(
                'Qual é o dia de vencimento da mensalidade?\n\n'
                'Digite um dia entre 1 e 28.\n\n'
                'Exemplo:\n'
                '10'
            ),
        )

    async def _apply_confirmed_student_due_day(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
        due_day: int,
    ) -> dict[str, str]:
        updated_context_data = dict(context_data)
        updated_context_data['due_day'] = due_day
        updated_context_data['is_exempt'] = False

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_CONFIRMATION,
            context_data=updated_context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=self._build_student_summary(updated_context_data),
            reply_markup=student_confirmation_reply_markup(),
        )

        return {'status': 'waiting_student_confirmation'}

    async def _resend_student_confirmation_message(
        self,
        chat_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=self._build_student_summary(context_data),
            reply_markup=student_confirmation_reply_markup(),
        )

        return {'status': 'waiting_student_confirmation'}

    async def _send_invalid_due_day_message(
        self,
        chat_id: int,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Dia de vencimento inválido.\n\n'
                'Digite um dia entre 1 e 28.\n\n'
                'Exemplo:\n'
                '10'
            ),
        )

    async def _process_skip(  # noqa: PLR0911
        self,
        chat_id: int,
        telegram_user_id: int,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if state is None:
            await self.send_menu(chat_id)

            return {'status': 'student_creation_state_not_found'}

        context_data = dict(state['context_data'])
        current_step = state['current_step']

        if current_step == TelegramStep.WAITING_STUDENT_ADDRESS_ZIP_CODE:
            return await self._skip_to_cpf(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_PHONE:
            return await self._ask_student_address_choice(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_IS_WHATSAPP:
            return await self._ask_student_address_choice(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_ADDRESS_STREET:
            updated_context_data = dict(context_data)
            address = dict(updated_context_data.get('address', {}))
            address['street'] = None
            updated_context_data['address'] = address

            await state_service.update_student_creation_context(
                state_id=state['id'],
                next_step=(TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD),
                context_data=updated_context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Agora digite o bairro do endereço.\n\n'
                    'Se não quiser informar agora, toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_address_neighborhood'}

        if current_step == TelegramStep.WAITING_STUDENT_ADDRESS_NEIGHBORHOOD:
            updated_context_data = dict(context_data)
            address = dict(updated_context_data.get('address', {}))
            address['neighborhood'] = None
            updated_context_data['address'] = address

            await state_service.update_student_creation_context(
                state_id=state['id'],
                next_step=TelegramStep.WAITING_STUDENT_ADDRESS_NUMBER,
                context_data=updated_context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=('Agora digite o número do endereço.\n\nExemplo:\n123'),
            )

            return {'status': 'waiting_student_address_number'}

        if current_step == TelegramStep.WAITING_STUDENT_ADDRESS_COMPLEMENT:
            updated_context_data = dict(context_data)
            address = dict(updated_context_data.get('address', {}))
            address['complement'] = None
            updated_context_data['address'] = address

            return await self._skip_to_cpf(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=updated_context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_CPF:
            return await self._skip_to_instagram(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_INSTAGRAM:
            await state_service.update_student_creation_context(
                state_id=state['id'],
                next_step=TelegramStep.WAITING_STUDENT_EMAIL,
                context_data=context_data,
            )

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Qual é o e-mail do aluno?\n\n'
                    'Se não quiser informar agora, toque em "⏭️ Pular".'
                ),
                reply_markup=optional_field_reply_markup(),
            )

            return {'status': 'waiting_student_email'}

        if current_step == TelegramStep.WAITING_STUDENT_EMAIL:
            return await self._skip_to_birth_date(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_RESPONSIBLE_EMAIL:
            current_responsible = dict(context_data['current_responsible'])
            current_responsible['email'] = None
            context_data['current_responsible'] = current_responsible

            return await self._finish_current_responsible(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_BIRTH_DATE:
            return await self._skip_to_monthly_fee(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        await self.send_menu(chat_id)

        return {'status': 'invalid_skip_step'}

    async def _ask_student_address_choice(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_CHOICE,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Como deseja informar o endereço do aluno?',
            reply_markup=student_address_choice_reply_markup(),
        )

        return {'status': 'waiting_student_address_choice'}

    async def _prompt_student_address_reference_search(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_REFERENCE_SEARCH,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Digite o nome do aluno que já possui o endereço '
                'que deseja reutilizar.'
            ),
        )

        return {'status': 'waiting_student_address_reference_search'}

    async def _prompt_student_responsible_reference_search(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_REFERENCE_SEARCH,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Digite o nome do aluno que já possui esse mesmo responsável.'
            ),
        )

        return {'status': 'waiting_student_responsible_reference_search'}

    async def _ask_student_address_zip_code(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_ADDRESS_ZIP_CODE,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o CEP do aluno?\n\n'
                'Digite apenas os números.\n\n'
                'Exemplo:\n'
                '74230110\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_address_zip_code'}

    async def _skip_to_cpf(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_CPF,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o CPF do aluno?\n\n'
                'Digite apenas os números, sem pontos ou traços.\n\n'
                'Exemplo:\n'
                '12345678911\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_cpf'}

    async def _skip_to_instagram(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_INSTAGRAM,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o Instagram do aluno?\n\n'
                'Digite sem @.\n\n'
                'Exemplo:\n'
                'joaosilva\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_instagram'}

    async def _skip_to_birth_date(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_BIRTH_DATE,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é a data de nascimento do aluno?\n\n'
                'Digite no formato dia/mês/ano.\n\n'
                'Exemplo:\n'
                '24/01/1994\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_birth_date'}

    async def _skip_to_monthly_fee(
        self,
        chat_id: int,
        state_id: int,
        context_data: dict[str, Any],
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_MONTHLY_FEE,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o valor da mensalidade do aluno?\n\n'
                'Exemplo:\n'
                '125\n'
                'ou\n'
                '100,50'
            ),
        )

        return {'status': 'waiting_student_monthly_fee'}

    async def _cancel_student_creation(
        self,
        chat_id: int,
        telegram_user_id: int,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if state is not None:
            await state_service.complete_current_flow(state['id'])

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Cadastro de aluno cancelado. ❌\n\nNenhum aluno foi salvo.'
            ),
            reply_markup=students_menu_reply_markup(),
        )

        return {'status': 'student_creation_cancelled'}

    async def _process_confirmation(
        self,
        chat_id: int,
        telegram_user_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_confirmation(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando confirmação.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_confirmation_state_not_found'}

        student = await self.student_service.create_from_telegram_context(
            academy_id=context.academy_id,
            context_data=state['context_data'],
        )

        await state_service.complete_current_flow(state['id'])

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Aluno cadastrado com sucesso! ✅\n\n'
                f'Nome: {student.name}\n\n'
                'Agora você pode consultar esse aluno na lista '
                'ou pela busca.'
            ),
            reply_markup=students_menu_reply_markup(),
        )

        return {'status': 'student_created'}

    async def _process_is_exempt_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        exempt_options = {
            'students:create:exempt:yes': True,
            'students:create:exempt:no': False,
        }
        is_exempt = exempt_options.get(callback_data)

        if is_exempt is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_is_exempt'}

        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_is_exempt(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando isenção.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_is_exempt_state_not_found'}

        context_data = dict(state['context_data'])
        context_data['is_exempt'] = is_exempt

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_CONFIRMATION,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=self._build_student_summary(context_data),
            reply_markup=student_confirmation_reply_markup(),
        )

        return {'status': 'waiting_student_confirmation'}

    @staticmethod
    def _get_student_id_from_details_callback(
        callback_data: str,
    ) -> int | None:
        raw_student_id = callback_data.removeprefix('students:details:')

        if not raw_student_id.isdigit():
            return None

        return int(raw_student_id)

    @staticmethod
    def _build_student_details_message(
        details: dict[str, Any],
    ) -> str:
        student = details['student']
        enrollments = details['enrollments']
        address = details.get('address')
        responsibles = details['responsibles']

        cpf = student.get('cpf')
        masked_cpf = 'Não informado'

        if cpf:
            masked_cpf = f'{cpf[:3]}.***.***-{cpf[-2:]}'

        birth_date = StudentsMenuHandler._format_birth_date_for_display(
            student.get('birth_date'),
        )
        whatsapp_text = StudentsMenuHandler._format_bool_text(
            student.get('phone_is_whatsapp'),
        )

        return (
            '👤 Detalhes do aluno\n\n'
            '📌 Informações pessoais\n'
            f'Nome: {student["name"]}\n'
            f'Sexo: {StudentsMenuHandler._format_sex(student.get("sex"))}\n'
            f'CPF: {masked_cpf}\n'
            f'Instagram: {student.get("instagram") or "Não informado"}\n'
            f'E-mail: {student.get("email") or "Não informado"}\n'
            f'Telefone: {student.get("phone") or "Não informado"}\n'
            f'WhatsApp: {whatsapp_text}\n'
            f'Data de nascimento: {birth_date}\n\n'
            f'{StudentsMenuHandler._build_enrollments_details(enrollments)}'
            f'{StudentsMenuHandler._build_address_details(address)}'
            f'{StudentsMenuHandler._build_responsibles_details(responsibles)}'
        )

    @staticmethod
    def _build_enrollments_details(
        enrollments: list[dict[str, Any]],
    ) -> str:
        if not enrollments:
            return '🥋 Matrícula\nNão há matrícula cadastrada.\n\n'

        lines = ['🥋 Matrícula']

        for enrollment in enrollments:
            status = StudentsMenuHandler._format_enum_value(
                enrollment['status'],
            )
            monthly_fee = enrollment.get('monthly_fee')
            due_day = enrollment.get('due_day')
            is_exempt = StudentsMenuHandler._format_bool_text(
                enrollment.get('is_exempt'),
            )

            lines.append(f'Modalidade: {enrollment["modality_name"]}')
            lines.append(f'Status: {status}')
            lines.append('')
            lines.append('💰 Mensalidade')
            lines.append(f'Valor: R$ {monthly_fee or "Não informado"}')
            lines.append(f'Vencimento: dia {due_day or "Não informado"}')
            lines.append(f'Isento: {is_exempt}')
            lines.append('')

        return '\n'.join(lines) + '\n'

    @staticmethod
    def _build_address_details(
        address: dict[str, Any] | None,
    ) -> str:
        if not address:
            return '🏠 Endereço\nNão informado\n\n'

        street = address.get('street') or 'Não informado'
        number = address.get('number') or 'S/N'
        neighborhood = address.get('neighborhood') or 'Não informado'
        city = address.get('city') or 'Não informado'
        state = address.get('state') or 'Não informado'
        zip_code = address.get('zip_code') or 'Não informado'
        complement = address.get('complement') or 'Não informado'

        return (
            '🏠 Endereço\n'
            f'Logradouro: {street}\n'
            f'Número: {number}\n'
            f'Bairro: {neighborhood}\n'
            f'Cidade/Estado: {city}/{state}\n'
            f'CEP: {zip_code}\n'
            f'Complemento: {complement}\n\n'
        )

    @staticmethod
    def _build_responsibles_details(
        responsibles: list[dict[str, Any]],
    ) -> str:
        if not responsibles:
            return '👨‍👩‍👧 Responsáveis\nNão há responsável externo.\n'

        lines = ['👨‍👩‍👧 Responsáveis']

        for responsible in responsibles:
            relationship = StudentsMenuHandler._get_relationship_label(
                responsible['relationship'],
            )
            whatsapp_text = StudentsMenuHandler._format_bool_text(
                responsible.get('phone_is_whatsapp'),
            )

            lines.append(f'{relationship}: {responsible["name"]}')
            lines.append(f'Telefone: {responsible["phone"]}')
            lines.append(f'WhatsApp: {whatsapp_text}')
            lines.append(
                f'E-mail: {responsible.get("email") or "Não informado"}'
            )
            lines.append('')

        return '\n'.join(lines).strip()

    @staticmethod
    def _format_bool_text(
        value: bool | None,
    ) -> str:
        if value is True:
            return 'Sim'

        if value is False:
            return 'Não'

        return 'Não informado'

    @staticmethod
    def _format_enum_value(
        value: Any,
    ) -> str:
        raw_value = getattr(value, 'value', value)

        return str(raw_value).replace('_', ' ').capitalize()

    @staticmethod
    def _format_sex(
        value: Any,
    ) -> str:
        raw_value = getattr(value, 'value', value)

        labels = {
            'male': 'Masculino',
            'masculino': 'Masculino',
            'female': 'Feminino',
            'feminino': 'Feminino',
            'other': 'Outros',
            'outros': 'Outros',
        }

        return labels.get(str(raw_value), 'Não informado')

    @staticmethod
    def _build_student_summary(
        context_data: dict[str, Any],
    ) -> str:
        cpf = context_data.get('cpf')
        masked_cpf = 'Não informado'

        if cpf:
            masked_cpf = f'{cpf[:3]}.***.***-{cpf[-2:]}'

        birth_date = StudentsMenuHandler._format_birth_date_for_display(
            context_data.get('birth_date'),
        )
        contact_summary = StudentsMenuHandler._build_contact_summary(
            context_data,
        )
        instagram = context_data.get('instagram')
        instagram_text = f'@{instagram}' if instagram else 'Não informado'

        responsibles_summary = StudentsMenuHandler._build_responsibles_summary(
            context_data
        )
        address_summary = StudentsMenuHandler._build_address_summary(
            context_data,
        )

        return (
            '📋 Resumo do cadastro\n\n'
            '👤 Aluno\n'
            f'Nome: {context_data["student_name"]}\n'
            f'Modalidade: {context_data["modality_name"]}\n'
            f'Sexo: {context_data["sex"].capitalize()}\n'
            f'CPF: {masked_cpf}\n'
            f'Instagram: {instagram_text}\n'
            f'E-mail: {context_data.get("email") or "Não informado"}\n'
            f'Data de nascimento: {birth_date}\n\n'
            f'{contact_summary}'
            f'{address_summary}'
            f'{responsibles_summary}'
            '💰 Mensalidade\n'
            f'Valor: R$ {context_data["monthly_fee"]}\n'
            f'Vencimento: dia {context_data["due_day"]}\n\n'
            'Está tudo certo?'
        )

    @staticmethod
    def _build_contact_summary(
        context_data: dict[str, Any],
    ) -> str:
        phone = context_data.get('phone')

        if not phone and context_data.get('responsible_type') == 'external':
            return ''

        is_whatsapp = context_data.get('is_whatsapp')
        whatsapp_text = 'Não informado'

        if is_whatsapp is True:
            whatsapp_text = 'Sim'
        elif is_whatsapp is False:
            whatsapp_text = 'Não'

        return (
            '📞 Contato\n'
            f'Telefone: {phone or "Não informado"}\n'
            f'WhatsApp: {whatsapp_text}\n\n'
        )

    @staticmethod
    def _build_address_summary(
        context_data: dict[str, Any],
    ) -> str:
        reused_from = context_data.get('address_reference_student_name')
        address = None

        if reused_from:
            address_reference = context_data.get('address_reference')

            if isinstance(address_reference, dict):
                address = address_reference

        if address is None:
            address = context_data.get('address')
            reused_from = None

        if address is None:
            address = context_data.get('address_reference')
            reused_from = context_data.get(
                'address_reference_student_name',
            )

        if not isinstance(address, dict):
            return '🏠 Endereço\nNão informado\n\n'

        street = address.get('street') or 'Não informado'
        number = address.get('number') or 'S/N'
        neighborhood = address.get('neighborhood') or 'Não informado'
        city = address.get('city') or 'Não informado'
        state = address.get('state') or 'Não informado'
        zip_code = address.get('zip_code') or 'Não informado'
        complement = address.get('complement') or 'Não informado'

        reused_text = ''

        if reused_from:
            reused_text = f'Reutilizado de: {reused_from}\n'

        return (
            '🏠 Endereço\n'
            f'{reused_text}'
            f'Logradouro: {street}\n'
            f'Número: {number}\n'
            f'Bairro: {neighborhood}\n'
            f'Cidade/Estado: {city}/{state}\n'
            f'CEP: {zip_code}\n'
            f'Complemento: {complement}\n\n'
        )

    @staticmethod
    def _build_responsibles_summary(
        context_data: dict[str, Any],
    ) -> str:
        responsibles = context_data.get('responsibles', [])
        responsible_references = context_data.get('responsible_references', [])

        if responsible_references and not responsibles:
            reference_details = context_data.get(
                'responsible_reference_details',
                [],
            )
            reference_student_name = context_data.get(
                'responsible_reference_student_name',
            )

            lines = ['👨‍👩‍👧 Responsáveis']

            if reference_student_name:
                lines.append(f'Reutilizado de: {reference_student_name}')

            if not reference_details:
                lines.append('Reutilizado de outro aluno')

                return '\n'.join(lines) + '\n\n'

            for responsible in reference_details:
                relationship = StudentsMenuHandler._get_relationship_label(
                    responsible['relationship'],
                )
                whatsapp_text = StudentsMenuHandler._format_bool_text(
                    responsible.get('phone_is_whatsapp'),
                )
                email_text = responsible.get('email') or 'Não informado'

                lines.append('')
                lines.append(f'{relationship}: {responsible["name"]}')
                lines.append(f'Telefone: {responsible["phone"]}')
                lines.append(f'WhatsApp: {whatsapp_text}')
                lines.append(f'E-mail: {email_text}')

            return '\n'.join(lines) + '\n\n'

        if not responsibles:
            if context_data.get('responsible_type') == 'self':
                return '👨‍👩‍👧 Responsáveis\nPróprio aluno\n\n'

            return '👨‍👩‍👧 Responsáveis\nNão informado\n\n'

        lines = ['👨‍👩‍👧 Responsáveis']

        for responsible in responsibles:
            relationship = StudentsMenuHandler._get_relationship_label(
                responsible['relationship'],
            )
            whatsapp_text = (
                'Sim' if responsible['phone_is_whatsapp'] else 'Não'
            )
            email_text = responsible.get('email') or 'Não informado'

            lines.append('')
            lines.append(f'{relationship}: {responsible["name"]}')
            lines.append(f'Telefone: {responsible["phone"]}')
            lines.append(f'WhatsApp: {whatsapp_text}')
            lines.append(f'E-mail: {email_text}')

        return '\n'.join(lines) + '\n\n'

    @staticmethod
    def _is_valid_email(
        email: str,
    ) -> bool:
        if '@' not in email:
            return False

        local_part, domain = email.split('@', maxsplit=1)

        return bool(local_part) and '.' in domain and bool(domain)

    @staticmethod
    def _format_birth_date_for_display(
        birth_date: Any,
    ) -> str:
        if not birth_date:
            return 'Não informado'

        if hasattr(birth_date, 'strftime'):
            return birth_date.strftime('%d/%m/%Y')

        year, month, day = str(birth_date).split('-')

        return f'{day}/{month}/{year}'

    @staticmethod
    def _get_relationship_label(
        relationship: str,
    ) -> str:
        labels = {
            'father': 'Pai',
            'mother': 'Mãe',
            'grandmother': 'Avó',
            'grandfather': 'Avô',
            'uncle': 'Tio',
            'aunt': 'Tia',
            'brother': 'Irmão',
            'sister': 'Irmã',
            'self': 'Próprio aluno',
        }

        return labels.get(relationship, relationship)

    async def _process_whatsapp_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        whatsapp_options = {
            'students:create:whatsapp:yes': True,
            'students:create:whatsapp:no': False,
        }
        is_whatsapp = whatsapp_options.get(callback_data)

        if is_whatsapp is None:
            await self.send_menu(chat_id)

            return {'status': 'invalid_student_whatsapp'}

        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_is_whatsapp(state):
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Não encontrei um cadastro aguardando WhatsApp.\n\n'
                    'Clique em "Cadastrar novo aluno" para começar novamente.'
                ),
                reply_markup=students_menu_reply_markup(),
            )

            return {'status': 'student_whatsapp_state_not_found'}

        context_data = dict(state['context_data'])
        context_data['is_whatsapp'] = is_whatsapp

        return await self._ask_student_address_choice(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Qual é o CPF do aluno?\n\n'
                'Digite apenas os números, sem pontos ou traços.\n\n'
                'Exemplo:\n'
                '12345678911\n\n'
                'Se não quiser informar agora, toque em "⏭️ Pular".'
            ),
            reply_markup=optional_field_reply_markup(),
        )

        return {'status': 'waiting_student_cpf'}

    async def _get_selected_modality(
        self,
        academy_id: int,
        modality_id: int,
    ) -> Any | None:
        modalities = await self.modality_service.list_selected_by_academy(
            academy_id
        )

        for modality in modalities:
            if modality.id == modality_id:
                return modality

        return None

    @staticmethod
    def _get_modality_id_from_callback(
        callback_data: str,
    ) -> int | None:
        raw_modality_id = callback_data.removeprefix(
            'students:create:modality:'
        )

        try:
            return int(raw_modality_id)
        except ValueError:
            return None

    @staticmethod
    def _is_waiting_student_modality(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_MODALITY
            and bool(state['context_data'].get('student_name'))
        )

    @staticmethod
    def _is_waiting_student_sex(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_SEX
            and bool(state['context_data'].get('student_name'))
            and bool(state['context_data'].get('modality_id'))
        )

    @staticmethod
    def _is_waiting_student_responsible_type(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_TYPE
            and bool(state['context_data'].get('student_name'))
            and bool(state['context_data'].get('modality_id'))
            and bool(state['context_data'].get('sex'))
        )

    @staticmethod
    def _is_waiting_student_responsible_relationship(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_RELATIONSHIP
            and state['context_data'].get('responsible_type') == 'external'
        )

    @staticmethod
    def _is_waiting_student_responsible_name(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        current_responsible = state['context_data'].get(
            'current_responsible',
            {},
        )

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_NAME
            and bool(current_responsible.get('relationship'))
        )

    @staticmethod
    def _is_waiting_student_field_confirmation(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_FIELD_CONFIRMATION
            and isinstance(
                state['context_data'].get(PENDING_FIELD_CONFIRMATION_KEY),
                dict,
            )
        )

    @staticmethod
    def _is_waiting_student_responsible_is_whatsapp(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        current_responsible = state['context_data'].get(
            'current_responsible',
            {},
        )

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_IS_WHATSAPP
            and bool(current_responsible.get('relationship'))
            and bool(current_responsible.get('name'))
            and bool(current_responsible.get('phone'))
        )

    @staticmethod
    def _is_waiting_student_responsible_next_action(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_RESPONSIBLE_NEXT_ACTION
            and bool(
                state['context_data'].get('responsibles')
                or state['context_data'].get('responsible_references')
            )
        )

    @staticmethod
    def _is_waiting_student_is_whatsapp(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_IS_WHATSAPP
            and bool(state['context_data'].get('phone'))
        )

    @staticmethod
    def _is_waiting_student_is_exempt(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step'] == TelegramStep.WAITING_STUDENT_IS_EXEMPT
            and bool(state['context_data'].get('student_name'))
            and bool(state['context_data'].get('modality_id'))
            and bool(state['context_data'].get('monthly_fee'))
            and bool(state['context_data'].get('due_day'))
        )

    @staticmethod
    def _is_waiting_student_confirmation(
        state: dict[str, Any] | None,
    ) -> bool:
        if state is None:
            return False

        return (
            state['current_flow'] == TelegramFlow.STUDENT_CREATION
            and state['current_step']
            == TelegramStep.WAITING_STUDENT_CONFIRMATION
            and bool(state['context_data'].get('student_name'))
            and bool(state['context_data'].get('modality_id'))
            and bool(state['context_data'].get('sex'))
            and bool(state['context_data'].get('monthly_fee'))
            and bool(state['context_data'].get('due_day'))
            and 'is_exempt' in state['context_data']
        )
