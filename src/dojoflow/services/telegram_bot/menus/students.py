from typing import Any

from dojoflow.schemas.modality import ModalityRead


def students_menu_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '➕ Cadastrar novo aluno',
                    'callback_data': 'students:create',
                },
            ],
            [
                {
                    'text': '📋 Lista de alunos',
                    'callback_data': 'students:list',
                },
            ],
            [
                {
                    'text': '🔎 Procurar aluno pelo nome',
                    'callback_data': 'students:search',
                },
            ],
            [
                {
                    'text': '🔙 Voltar ao menu',
                    'callback_data': 'menu:main',
                },
            ],
        ]
    }


def student_modalities_reply_markup(
    modalities: list[ModalityRead],
) -> dict[str, Any]:
    inline_keyboard: list[list[dict[str, str]]] = []

    for modality in modalities:
        inline_keyboard.append([
            {
                'text': modality.name,
                'callback_data': (f'students:create:modality:{modality.id}'),
            },
        ])

    inline_keyboard.append([
        {
            'text': '❌ Cancelar cadastro',
            'callback_data': 'students:create:cancel',
        },
    ])

    return {
        'inline_keyboard': inline_keyboard,
    }


def student_sex_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': 'Masculino',
                    'callback_data': 'students:create:sex:male',
                },
            ],
            [
                {
                    'text': 'Feminino',
                    'callback_data': 'students:create:sex:female',
                },
            ],
            [
                {
                    'text': 'Outros',
                    'callback_data': 'students:create:sex:other',
                },
            ],
            [
                {
                    'text': '❌ Cancelar cadastro',
                    'callback_data': 'students:create:cancel',
                },
            ],
        ]
    }


def optional_field_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '⏭️ Pular',
                    'callback_data': 'students:create:skip',
                },
            ],
            [
                {
                    'text': '❌ Cancelar cadastro',
                    'callback_data': 'students:create:cancel',
                },
            ],
        ]
    }


def yes_no_skip_reply_markup(
    yes_callback_data: str,
    no_callback_data: str,
) -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '✅ Sim',
                    'callback_data': yes_callback_data,
                },
            ],
            [
                {
                    'text': '❌ Não',
                    'callback_data': no_callback_data,
                },
            ],
            [
                {
                    'text': '⏭️ Pular',
                    'callback_data': 'students:create:skip',
                },
            ],
        ]
    }


def yes_no_required_reply_markup(
    yes_callback_data: str,
    no_callback_data: str,
) -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '✅ Sim',
                    'callback_data': yes_callback_data,
                },
            ],
            [
                {
                    'text': '❌ Não',
                    'callback_data': no_callback_data,
                },
            ],
            [
                {
                    'text': '❌ Cancelar cadastro',
                    'callback_data': 'students:create:cancel',
                },
            ],
        ]
    }


def student_confirmation_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '✅ Confirmar cadastro',
                    'callback_data': 'students:create:confirm',
                },
            ],
            [
                {
                    'text': '✏️ Corrigir dados',
                    'callback_data': 'students:create:edit',
                },
            ],
            [
                {
                    'text': '❌ Cancelar cadastro',
                    'callback_data': 'students:create:cancel',
                },
            ],
        ]
    }
