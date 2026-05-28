from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.services.telegram_bot.menus.students import (
    students_menu_reply_markup,
)


class StudentsMenuHandler:
    def __init__(
        self,
        telegram_service: TelegramService,
    ) -> None:
        self.telegram_service = telegram_service

    async def send_menu(
        self,
        chat_id: int,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '👥 Alunos\n\n'
                'Escolha uma opção abaixo 👇'
            ),
            reply_markup=students_menu_reply_markup(),
        )

    async def process_callback(
        self,
        chat_id: int,
        callback_data: str,
    ) -> dict[str, str]:
        students_option_messages = {
            'students:create': (
                '➕ Cadastrar novo aluno\n\n'
                'Aqui vamos iniciar o cadastro de um novo aluno.\n\n'
                'Esse fluxo será implementado no próximo passo.'
            ),
            'students:list': (
                '📋 Lista de alunos\n\n'
                'Aqui vamos listar os alunos cadastrados na academia.\n\n'
                'Esse fluxo será implementado no próximo passo.'
            ),
            'students:search': (
                '🔎 Procurar aluno pelo nome\n\n'
                'Aqui vamos buscar um aluno específico pelo nome.\n\n'
                'Esse fluxo será implementado no próximo passo.'
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
