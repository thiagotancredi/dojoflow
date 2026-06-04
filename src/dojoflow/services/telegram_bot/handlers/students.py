from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.modality import ModalityService
from dojoflow.services.student import StudentService
from dojoflow.services.telegram_bot.menus.students import (
    optional_field_reply_markup,
    student_confirmation_reply_markup,
    student_modalities_reply_markup,
    student_responsible_next_action_reply_markup,
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
MIN_INSTAGRAM_LENGTH = 2
BIRTH_DATE_FORMAT = '%d/%m/%Y'
MONEY_DECIMAL_PLACES = Decimal('0.01')
MIN_MONTHLY_FEE = Decimal('0')
MIN_DUE_DAY = 1
MAX_DUE_DAY = 28


class StudentsMenuHandler:
    def __init__(
        self,
        telegram_service: TelegramService,
        telegram_conversation_state_service: (
            TelegramConversationStateService
        ),
        modality_service: ModalityService,
        student_service: StudentService,
    ) -> None:
        self.telegram_service = telegram_service
        self.telegram_conversation_state_service = (
            telegram_conversation_state_service
        )
        self.modality_service = modality_service
        self.student_service = student_service

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

        if callback_data == 'students:create:cancel':
            return await self._cancel_student_creation(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
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

        if callback_data.startswith(
            'students:create:responsible:relationship:'
        ):
            return await self._process_responsible_relationship_choice(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                callback_data=callback_data,
            )

        if callback_data.startswith(
            'students:create:responsible:whatsapp:'
        ):
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
            reply_markup={
                'inline_keyboard': [
                    [
                        {
                            'text': '💰 Ver mensalidades',
                            'callback_data': (
                                f'students:payments:{student_id}'
                            ),
                        },
                    ],
                    [
                        {
                            'text': '✏️ Editar aluno',
                            'callback_data': f'students:edit:{student_id}',
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

        return {'status': 'student_details_sent'}

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

        context_data = {
            'student_name': normalized_student_name,
        }

        state_service = self.telegram_conversation_state_service

        await state_service.update_student_creation_context(
            state_id=state_id,
            next_step=TelegramStep.WAITING_STUDENT_MODALITY,
            context_data=context_data,
        )

        modalities = await self.modality_service.list_selected_by_academy(
            context.academy_id
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Perfeito! ✅\n\n'
                f'Aluno: {normalized_student_name}\n\n'
                'Agora escolha a modalidade do aluno:'
            ),
            reply_markup=student_modalities_reply_markup(modalities),
        )

        return {'status': 'waiting_student_modality'}

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
                'Qual é o nome completo do aluno?'
            ),
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

        updated_context_data = dict(context_data)
        updated_context_data['phone'] = normalized_phone

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

        await state_service.update_student_creation_context(
            state_id=state['id'],
            next_step=TelegramStep.WAITING_STUDENT_RESPONSIBLE_RELATIONSHIP,
            context_data=context_data,
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text='Qual é o parentesco do responsável?',
            reply_markup=student_responsible_relationship_reply_markup(),
        )

        return {'status': 'waiting_student_responsible_relationship'}

    async def _process_responsible_relationship_choice(
        self,
        chat_id: int,
        telegram_user_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        state_service = self.telegram_conversation_state_service
        state = await state_service.get_by_telegram_user_id(telegram_user_id)

        if not self._is_waiting_student_responsible_relationship(state):
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
            text='Qual é o nome do responsável?',
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

        updated_context_data = dict(context_data)
        current_responsible = dict(
            updated_context_data['current_responsible']
        )
        current_responsible['name'] = normalized_responsible_name
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

        updated_context_data = dict(context_data)
        current_responsible = dict(
            updated_context_data['current_responsible']
        )
        current_responsible['phone'] = normalized_phone
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
                yes_callback_data=(
                    'students:create:responsible:whatsapp:yes'
                ),
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
                text='Qual é o parentesco do responsável?',
                reply_markup=student_responsible_relationship_reply_markup(),
            )

            return {'status': 'waiting_student_responsible_relationship'}

        return await self._skip_to_cpf(
            chat_id=chat_id,
            state_id=state['id'],
            context_data=context_data,
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

        updated_context_data = dict(context_data)
        updated_context_data['cpf'] = normalized_cpf

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
        normalized_instagram = instagram.strip().removeprefix('@').strip()

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

        updated_context_data = dict(context_data)
        updated_context_data['instagram'] = normalized_instagram

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

            return {'status': 'invalid_student_email'}

        updated_context_data = dict(context_data)
        updated_context_data['email'] = normalized_email

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

        updated_context_data = dict(context_data)
        current_responsible = dict(
            updated_context_data['current_responsible']
        )
        current_responsible['email'] = normalized_email
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
        current_responsible = dict(
            updated_context_data['current_responsible']
        )

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

        updated_context_data = dict(context_data)
        updated_context_data['birth_date'] = birth_date.isoformat()

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
        normalized_monthly_fee = monthly_fee_text.strip().replace(',', '.')

        try:
            monthly_fee = Decimal(normalized_monthly_fee)
        except InvalidOperation:
            await self._send_invalid_monthly_fee_message(chat_id)

            return {'status': 'invalid_student_monthly_fee'}

        if monthly_fee <= MIN_MONTHLY_FEE:
            await self._send_invalid_monthly_fee_message(chat_id)

            return {'status': 'invalid_student_monthly_fee'}

        monthly_fee = monthly_fee.quantize(MONEY_DECIMAL_PLACES)

        updated_context_data = dict(context_data)
        updated_context_data['monthly_fee'] = str(monthly_fee)

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
        try:
            due_day = int(due_day_text.strip())
        except ValueError:
            await self._send_invalid_due_day_message(chat_id)

            return {'status': 'invalid_student_due_day'}

        if not MIN_DUE_DAY <= due_day <= MAX_DUE_DAY:
            await self._send_invalid_due_day_message(chat_id)

            return {'status': 'invalid_student_due_day'}

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

        if current_step == TelegramStep.WAITING_STUDENT_PHONE:
            return await self._skip_to_cpf(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
            )

        if current_step == TelegramStep.WAITING_STUDENT_IS_WHATSAPP:
            return await self._skip_to_cpf(
                chat_id=chat_id,
                state_id=state['id'],
                context_data=context_data,
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
        state = await state_service.get_by_telegram_user_id(
            telegram_user_id
        )

        if state is not None:
            await state_service.complete_current_flow(state['id'])

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Cadastro de aluno cancelado. ❌\n\n'
                'Nenhum aluno foi salvo.'
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
        state = await state_service.get_by_telegram_user_id(
            telegram_user_id
        )

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

        is_whatsapp = context_data.get('is_whatsapp')
        whatsapp_text = 'Não informado'

        if is_whatsapp is True:
            whatsapp_text = 'Sim'
        elif is_whatsapp is False:
            whatsapp_text = 'Não'

        birth_date = StudentsMenuHandler._format_birth_date_for_display(
            context_data.get('birth_date'),
        )
        responsibles_summary = (
            StudentsMenuHandler._build_responsibles_summary(context_data)
        )

        return (
            '📋 Resumo do cadastro do aluno\n\n'
            f'Nome: {context_data["student_name"]}\n'
            f'Modalidade: {context_data["modality_name"]}\n'
            f'Sexo: {context_data["sex"].capitalize()}\n'
            f'Telefone: {context_data.get("phone") or "Não informado"}\n'
            f'WhatsApp: {whatsapp_text}\n'
            f'{responsibles_summary}'
            f'CPF: {masked_cpf}\n'
            f'Instagram: {context_data.get("instagram") or "Não informado"}\n'
            f'E-mail: {context_data.get("email") or "Não informado"}\n'
            f'Data de nascimento: {birth_date}\n'
            f'Mensalidade: R$ {context_data["monthly_fee"]}\n'
            f'Vencimento: dia {context_data["due_day"]}\n\n'
            'Está tudo certo?'
        )

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
    def _build_responsibles_summary(
        context_data: dict[str, Any],
    ) -> str:
        responsibles = context_data.get('responsibles', [])

        if not responsibles:
            if context_data.get('responsible_type') == 'self':
                return 'Responsável: próprio aluno\n'

            return 'Responsável: Não informado\n'

        lines = ['Responsáveis:']

        for responsible in responsibles:
            relationship = StudentsMenuHandler._get_relationship_label(
                responsible['relationship'],
            )
            whatsapp_text = (
                'Sim' if responsible['phone_is_whatsapp'] else 'Não'
            )

            email_text = responsible.get('email') or 'Não informado'

            lines.append(
                '- '
                f'{relationship}: {responsible["name"]} '
                f'({responsible["phone"]}, WhatsApp: {whatsapp_text}, '
                f'E-mail: {email_text})'
            )

        return '\n'.join(lines) + '\n'

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

        await state_service.update_student_creation_context(
            state_id=state['id'],
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
            and bool(state['context_data'].get('responsibles'))
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
