from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.services.modality import ModalityService
from dojoflow.services.telegram_bot.menus.main import main_menu_reply_markup
from dojoflow.services.telegram_bot.menus.modalities import (
    academy_modalities_reply_markup,
)


class AcademyModalitiesHandler:
    def __init__(
        self,
        telegram_service: TelegramService,
        modality_service: ModalityService,
    ) -> None:
        self.telegram_service = telegram_service
        self.modality_service = modality_service

    async def send_selection_menu(
        self,
        chat_id: int,
        context: MasterContextRead,
    ) -> None:
        options = await self.modality_service.list_academy_options(
            context.academy_id
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                '🏫 Modalidades da academia\n\n'
                'Selecione as modalidades que existem na sua academia.\n\n'
                'Toque em uma modalidade para marcar ou desmarcar.'
            ),
            reply_markup=academy_modalities_reply_markup(options),
        )

    async def process_callback(
        self,
        chat_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        if callback_data == 'menu:academy':
            await self.send_selection_menu(
                chat_id=chat_id,
                context=context,
            )

            return {'status': 'academy_modalities_menu_sent'}

        if callback_data == 'academy_modalities:finish':
            return await self._finish_setup(
                chat_id=chat_id,
                context=context,
            )

        if callback_data.startswith('academy_modalities:toggle:'):
            return await self._toggle_modality(
                chat_id=chat_id,
                callback_data=callback_data,
                context=context,
            )

        await self.send_selection_menu(
            chat_id=chat_id,
            context=context,
        )

        return {'status': 'unknown_academy_modalities_callback'}

    async def _toggle_modality(
        self,
        chat_id: int,
        callback_data: str,
        context: MasterContextRead,
    ) -> dict[str, str]:
        try:
            modality_id = int(
                callback_data.removeprefix('academy_modalities:toggle:')
            )
        except ValueError:
            await self.send_selection_menu(
                chat_id=chat_id,
                context=context,
            )

            return {'status': 'invalid_modality_id'}

        was_selected = await self.modality_service.toggle_academy_modality(
            academy_id=context.academy_id,
            modality_id=modality_id,
        )

        message = (
            'Modalidade marcada com sucesso. ✅'
            if was_selected
            else 'Modalidade desmarcada com sucesso.'
        )

        options = await self.modality_service.list_academy_options(
            context.academy_id
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                f'{message}\n\nAtualizei a lista de modalidades da academia.'
            ),
            reply_markup=academy_modalities_reply_markup(options),
        )

        return {'status': 'academy_modality_toggled'}

    async def _finish_setup(
        self,
        chat_id: int,
        context: MasterContextRead,
    ) -> dict[str, str]:
        has_selected_modalities = (
            await self.modality_service.has_selected_modalities(
                context.academy_id
            )
        )

        if not has_selected_modalities:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=(
                    'Selecione pelo menos uma modalidade para continuar. 🥋'
                ),
            )

            await self.send_selection_menu(
                chat_id=chat_id,
                context=context,
            )

            return {'status': 'academy_modalities_required'}

        selected_modalities = (
            await self.modality_service.list_selected_by_academy(
                context.academy_id
            )
        )

        modality_names = '\n'.join(
            f'• {modality.name}' for modality in selected_modalities
        )

        await self.telegram_service.send_message(
            chat_id=chat_id,
            text=(
                'Modalidades configuradas com sucesso! ✅\n\n'
                'Modalidades vinculadas à sua academia:\n'
                f'{modality_names}\n\n'
                'Agora sua academia já está pronta para cadastrar alunos.\n\n'
                'Escolha uma opção abaixo 👇'
            ),
            reply_markup=main_menu_reply_markup(),
        )

        return {'status': 'academy_modalities_finished'}
