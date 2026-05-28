from typing import Any


def main_menu_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '👥 Alunos',
                    'callback_data': 'menu:students',
                },
                {
                    'text': '💰 Mensalidades',
                    'callback_data': 'menu:monthly_fees',
                },
            ],
            [
                {
                    'text': '✅ Pagamentos',
                    'callback_data': 'menu:payments',
                },
                {
                    'text': '📊 Relatórios',
                    'callback_data': 'menu:reports',
                },
            ],
            [
                {
                    'text': '🏫 Minha academia',
                    'callback_data': 'menu:academy',
                },
            ],
            [
                {
                    'text': '❓ Ajuda',
                    'callback_data': 'menu:help',
                },
            ],
        ]
    }
