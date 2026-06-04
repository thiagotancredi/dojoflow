from typing import Any

from dojoflow.schemas.modality import ModalityOptionRead


def academy_modalities_reply_markup(
    options: list[ModalityOptionRead],
) -> dict[str, Any]:
    inline_keyboard: list[list[dict[str, str]]] = []

    for option in options:
        selected_marker = '✓ ' if option.is_selected else ''
        button_text = f'{selected_marker}{option.name}'

        inline_keyboard.append([
            {
                'text': button_text,
                'callback_data': (f'academy_modalities:toggle:{option.id}'),
            },
        ])

    inline_keyboard.append([
        {
            'text': '✅ Concluir',
            'callback_data': 'academy_modalities:finish',
        },
    ])
    inline_keyboard.append([
        {
            'text': '🔙 Voltar ao menu',
            'callback_data': 'menu:main',
        },
    ])

    return {
        'inline_keyboard': inline_keyboard,
    }
