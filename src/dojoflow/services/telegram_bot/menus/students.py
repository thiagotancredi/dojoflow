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


def student_responsible_type_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '🙋 Sim, é o próprio responsável',
                    'callback_data': 'students:create:responsible:self',
                },
            ],
            [
                {
                    'text': '👨‍👩‍👧 Não, possui responsável',
                    'callback_data': 'students:create:responsible:external',
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


def student_responsible_relationship_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': 'Pai',
                    'callback_data': (
                        'students:create:responsible:relationship:father'
                    ),
                },
                {
                    'text': 'Mãe',
                    'callback_data': (
                        'students:create:responsible:relationship:mother'
                    ),
                },
            ],
            [
                {
                    'text': 'Avó',
                    'callback_data': (
                        'students:create:responsible:relationship:grandmother'
                    ),
                },
                {
                    'text': 'Avô',
                    'callback_data': (
                        'students:create:responsible:relationship:grandfather'
                    ),
                },
            ],
            [
                {
                    'text': 'Tio',
                    'callback_data': (
                        'students:create:responsible:relationship:uncle'
                    ),
                },
                {
                    'text': 'Tia',
                    'callback_data': (
                        'students:create:responsible:relationship:aunt'
                    ),
                },
            ],
            [
                {
                    'text': 'Irmão',
                    'callback_data': (
                        'students:create:responsible:relationship:brother'
                    ),
                },
                {
                    'text': 'Irmã',
                    'callback_data': (
                        'students:create:responsible:relationship:sister'
                    ),
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


def student_responsible_next_action_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '➕ Cadastrar mais um responsável',
                    'callback_data': 'students:create:responsible:add',
                },
            ],
            [
                {
                    'text': '✅ Continuar cadastro',
                    'callback_data': 'students:create:responsible:continue',
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
                    'text': '❌ Cancelar cadastro',
                    'callback_data': 'students:create:cancel',
                },
            ],
        ]
    }
