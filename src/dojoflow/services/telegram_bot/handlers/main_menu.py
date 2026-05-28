from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.telegram_bot.menus.main import main_menu_reply_markup


class MainMenuHandler:
    def __init__(
        self,
        telegram_service: TelegramService,
    ) -> None:
        self.telegram_service = telegram_service

    async def send_menu(
        self,
        chat_id: int,
        context: MasterContextRead,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                f'Olá, {context.master_name}! 🥋\n\n'
                f'🏫 Academia: {context.academy_name}\n\n'
                'Escolha uma opção abaixo 👇'
            ),
            reply_markup=main_menu_reply_markup(),
        )

    async def send_help(
        self,
        chat_id: int,
    ) -> None:
        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '❓ Ajuda - DojoFlow 🥋\n\n'
                'Use os botões do menu para navegar pelo sistema.\n\n'
                'Opções disponíveis:\n'
                '👥 Alunos: cadastrar, listar e buscar alunos.\n'
                '💰 Mensalidades: ver mensalidades em aberto, atrasadas, '
                'pagas e isentas.\n'
                '✅ Pagamentos: registrar pagamento normal, parcial '
                'ou adiantado.\n'
                '📊 Relatórios: ver resumo financeiro e taxas.\n'
                '🏫 Minha academia: alterar seus dados, dados da academia '
                'e modalidades.\n\n'
                'Comandos úteis:\n'
                '📌 menu - mostra o menu principal\n'
                '❌ cancelar - cancela a operação atual\n'
                '❓ ajuda - mostra esta mensagem novamente'
            ),
            reply_markup=main_menu_reply_markup(),
        )

    async def process_callback(
        self,
        chat_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        if callback_data == 'menu:main':
            await self.send_menu(
                chat_id=chat_id,
                context=context,
            )

            return {'status': 'main_menu_sent'}

        if callback_data == 'menu:help':
            await self.send_help(chat_id)

            return {'status': 'help_sent'}

        option_messages = {
            'menu:monthly_fees': (
                '💰 Mensalidades\n\n'
                'Aqui você vai poder ver mensalidades em aberto, atrasadas, '
                'pagas, isentas e pendentes de configuração.\n\n'
                'Vamos implementar esse fluxo em seguida.'
            ),
            'menu:payments': (
                '✅ Pagamentos\n\n'
                'Aqui você vai poder registrar pagamento normal, parcial '
                'ou adiantado.\n\n'
                'Vamos implementar esse fluxo em seguida.'
            ),
            'menu:reports': (
                '📊 Relatórios\n\n'
                'Aqui você vai ver o resumo financeiro, porcentagens, '
                'isentos e taxas de maquininha.\n\n'
                'Vamos implementar esse fluxo em seguida.'
            ),
            'menu:academy': (
                '🏫 Minha academia\n\n'
                'Aqui você vai poder alterar seu nome, o nome da academia, '
                'telefone e modalidades.\n\n'
                'Vamos implementar esse fluxo em seguida.'
            ),
        }

        message = option_messages.get(callback_data)

        if message is None:
            await self.send_menu(
                chat_id=chat_id,
                context=context,
            )

            return {'status': 'unknown_callback'}

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=message,
        )

        return {'status': 'menu_option_selected'}
