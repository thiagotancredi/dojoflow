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


def student_creation_cancel_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '❌ Cancelar cadastro',
                    'callback_data': 'students:create:cancel',
                },
            ],
        ],
    }


def student_details_reply_markup(
    student_id: int,
) -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '💰 Ver mensalidades',
                    'callback_data': f'students:payments:{student_id}',
                },
            ],
            [
                {
                    'text': '✏️ Editar',
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
    }


def student_edit_menu_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '👤 Dados do aluno',
                    'callback_data': 'students:edit:section:basic',
                },
            ],
            [
                {
                    'text': '🏠 Endereço',
                    'callback_data': 'students:edit:section:address',
                },
            ],
            [
                {
                    'text': '👥 Responsáveis',
                    'callback_data': 'students:edit:section:responsibles',
                },
            ],
            [
                {
                    'text': '💰 Mensalidade',
                    'callback_data': 'students:edit:section:monthly_fee',
                },
            ],
            [
                {
                    'text': '📌 Status da matrícula',
                    'callback_data': 'students:edit:section:status',
                },
            ],
            [
                {
                    'text': '🔙 Voltar aos detalhes',
                    'callback_data': 'students:edit:back:details',
                },
            ],
        ],
    }


def student_edit_basic_data_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': 'Nome',
                    'callback_data': 'students:edit:field:name',
                },
            ],
            [
                {
                    'text': 'Modalidade',
                    'callback_data': 'students:edit:field:modality',
                },
            ],
            [
                {
                    'text': 'Sexo',
                    'callback_data': 'students:edit:field:sex',
                },
            ],
            [
                {
                    'text': 'CPF',
                    'callback_data': 'students:edit:field:cpf',
                },
            ],
            [
                {
                    'text': 'Instagram',
                    'callback_data': 'students:edit:field:instagram',
                },
            ],
            [
                {
                    'text': 'Data de nascimento',
                    'callback_data': 'students:edit:field:birth_date',
                },
            ],
            [
                {
                    'text': 'E-mail',
                    'callback_data': 'students:edit:field:email',
                },
            ],
            [
                {
                    'text': '🔙 Voltar para edição',
                    'callback_data': 'students:edit:back:menu',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ],
    }


def student_edit_address_reply_markup(
    *,
    has_address: bool,
) -> dict[str, Any]:
    inline_keyboard: list[list[dict[str, str]]] = [
        [
            {
                'text': '📝 Informar novo endereço',
                'callback_data': 'students:edit:address:new',
            },
        ],
        [
            {
                'text': '🔁 Usar endereço de outro aluno',
                'callback_data': 'students:edit:address:reuse',
            },
        ],
    ]

    if has_address:
        inline_keyboard.append([
            {
                'text': '🧹 Remover endereço',
                'callback_data': 'students:edit:address:remove',
            },
        ])

    inline_keyboard.append([
        {
            'text': '🔙 Voltar para edição',
            'callback_data': 'students:edit:back:menu',
        },
    ])
    inline_keyboard.append([
        {
            'text': '❌ Cancelar edição',
            'callback_data': 'students:edit:cancel',
        },
    ])

    return {
        'inline_keyboard': inline_keyboard,
    }


def student_edit_responsibles_reply_markup(
    *,
    has_responsibles: bool,
) -> dict[str, Any]:
    inline_keyboard: list[list[dict[str, str]]] = [
        [
            {
                'text': '➕ Adicionar responsável',
                'callback_data': 'students:edit:responsibles:new',
            },
        ],
        [
            {
                'text': '🔁 Usar responsável de outro aluno',
                'callback_data': 'students:edit:responsibles:reuse',
            },
        ],
    ]

    if has_responsibles:
        inline_keyboard.append([
            {
                'text': '🧹 Remover responsável',
                'callback_data': 'students:edit:responsibles:remove',
            },
        ])

    inline_keyboard.append([
        {
            'text': '🔙 Voltar para edição',
            'callback_data': 'students:edit:back:menu',
        },
    ])
    inline_keyboard.append([
        {
            'text': '❌ Cancelar edição',
            'callback_data': 'students:edit:cancel',
        },
    ])

    return {
        'inline_keyboard': inline_keyboard,
    }


def student_edit_monthly_fee_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': 'Valor da mensalidade',
                    'callback_data': 'students:edit:monthly_fee:monthly_fee',
                },
            ],
            [
                {
                    'text': 'Dia de vencimento',
                    'callback_data': 'students:edit:monthly_fee:due_day',
                },
            ],
            [
                {
                    'text': '🔙 Voltar para edição',
                    'callback_data': 'students:edit:back:menu',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ],
    }


def student_edit_address_number_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '🔁 Digitar outro CEP',
                    'callback_data': 'students:edit:address:change_zip',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ]
    }


def student_edit_optional_field_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '⏭️ Pular',
                    'callback_data': 'students:edit:address:skip',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ]
    }


def student_edit_skip_field_reply_markup(
    skip_callback_data: str,
) -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '⏭️ Pular',
                    'callback_data': skip_callback_data,
                },
            ],
            [
                {
                    'text': '🔙 Voltar',
                    'callback_data': 'students:edit:back',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ]
    }


def student_edit_prompt_reply_markup(
    *,
    remove_callback_data: str | None = None,
) -> dict[str, Any]:
    inline_keyboard: list[list[dict[str, str]]] = []

    if remove_callback_data is not None:
        inline_keyboard.append([
            {
                'text': '🧹 Remover informação',
                'callback_data': remove_callback_data,
            },
        ])

    inline_keyboard.append([
        {
            'text': '🔙 Voltar',
            'callback_data': 'students:edit:back',
        },
    ])
    inline_keyboard.append([
        {
            'text': '❌ Cancelar edição',
            'callback_data': 'students:edit:cancel',
        },
    ])

    return {
        'inline_keyboard': inline_keyboard,
    }


def student_edit_confirmation_reply_markup(
    *,
    include_rewrite: bool = True,
    confirm_label: str = '✅ Confirmar alteração',
    rewrite_label: str = '✏️ Reescrever',
) -> dict[str, Any]:
    inline_keyboard: list[list[dict[str, str]]] = [
        [
            {
                'text': confirm_label,
                'callback_data': 'students:edit:confirm',
            },
        ],
    ]

    if include_rewrite:
        inline_keyboard.append([
            {
                'text': rewrite_label,
                'callback_data': 'students:edit:rewrite',
            },
        ])

    inline_keyboard.append([
        {
            'text': '🔙 Voltar',
            'callback_data': 'students:edit:back',
        },
    ])
    inline_keyboard.append([
        {
            'text': '❌ Cancelar edição',
            'callback_data': 'students:edit:cancel',
        },
    ])

    return {
        'inline_keyboard': inline_keyboard,
    }


def student_edit_field_confirmation_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '✅ Confirmar',
                    'callback_data': 'students:edit:field:confirm',
                },
            ],
            [
                {
                    'text': '✏️ Reescrever',
                    'callback_data': 'students:edit:field:rewrite',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ]
    }


def student_edit_responsible_relationship_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': 'Pai',
                    'callback_data': (
                        'students:edit:responsibles:relationship:father'
                    ),
                },
            ],
            [
                {
                    'text': 'Mãe',
                    'callback_data': (
                        'students:edit:responsibles:relationship:mother'
                    ),
                },
            ],
            [
                {
                    'text': 'Avó',
                    'callback_data': (
                        'students:edit:responsibles:relationship:grandmother'
                    ),
                },
            ],
            [
                {
                    'text': 'Avô',
                    'callback_data': (
                        'students:edit:responsibles:relationship:grandfather'
                    ),
                },
            ],
            [
                {
                    'text': 'Tio',
                    'callback_data': (
                        'students:edit:responsibles:relationship:uncle'
                    ),
                },
            ],
            [
                {
                    'text': 'Tia',
                    'callback_data': (
                        'students:edit:responsibles:relationship:aunt'
                    ),
                },
            ],
            [
                {
                    'text': 'Irmão',
                    'callback_data': (
                        'students:edit:responsibles:relationship:brother'
                    ),
                },
            ],
            [
                {
                    'text': 'Irmã',
                    'callback_data': (
                        'students:edit:responsibles:relationship:sister'
                    ),
                },
            ],
            [
                {
                    'text': '🔙 Voltar',
                    'callback_data': 'students:edit:back',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ]
    }


def student_edit_responsible_whatsapp_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '✅ Sim',
                    'callback_data': 'students:edit:responsibles:whatsapp:yes',
                },
            ],
            [
                {
                    'text': '❌ Não',
                    'callback_data': 'students:edit:responsibles:whatsapp:no',
                },
            ],
            [
                {
                    'text': '🔙 Voltar',
                    'callback_data': 'students:edit:back',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
                },
            ],
        ]
    }


def student_edit_responsible_reference_search_actions_rows(
) -> list[list[dict[str, str]]]:
    return [
        [
            {
                'text': '🔎 Pesquisar novamente',
                'callback_data': 'students:edit:responsibles:search_again',
            },
        ],
        [
            {
                'text': '🔙 Voltar para opções de responsáveis',
                'callback_data': 'students:edit:responsibles:back',
            },
        ],
        [
            {
                'text': '❌ Cancelar edição',
                'callback_data': 'students:edit:cancel',
            },
        ],
    ]


def student_edit_modalities_reply_markup(
    modalities: list[ModalityRead],
) -> dict[str, Any]:
    inline_keyboard: list[list[dict[str, str]]] = []

    for modality in modalities:
        inline_keyboard.append([
            {
                'text': modality.name,
                'callback_data': f'students:edit:modality:{modality.id}',
            },
        ])

    inline_keyboard.append([
        {
            'text': '🔙 Voltar',
            'callback_data': 'students:edit:back',
        },
    ])
    inline_keyboard.append([
        {
            'text': '❌ Cancelar edição',
            'callback_data': 'students:edit:cancel',
        },
    ])

    return {
        'inline_keyboard': inline_keyboard,
    }


def student_edit_sex_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': 'Masculino',
                    'callback_data': 'students:edit:sex:male',
                },
            ],
            [
                {
                    'text': 'Feminino',
                    'callback_data': 'students:edit:sex:female',
                },
            ],
            [
                {
                    'text': 'Outros',
                    'callback_data': 'students:edit:sex:other',
                },
            ],
            [
                {
                    'text': '🔙 Voltar',
                    'callback_data': 'students:edit:back',
                },
            ],
            [
                {
                    'text': '❌ Cancelar edição',
                    'callback_data': 'students:edit:cancel',
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


def student_responsible_choice_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '👤 Cadastrar novo responsável',
                    'callback_data': 'students:create:responsible:new',
                },
            ],
            [
                {
                    'text': '🔁 Usar responsável de outro aluno',
                    'callback_data': 'students:create:responsible:reuse',
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


def student_address_choice_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '🏠 Cadastrar novo endereço',
                    'callback_data': 'students:create:address:new',
                }
            ],
            [
                {
                    'text': '🔁 Usar endereço de outro aluno',
                    'callback_data': 'students:create:address:reuse',
                }
            ],
            [
                {
                    'text': '⏭️ Pular endereço',
                    'callback_data': 'students:create:address:skip',
                }
            ],
            [
                {
                    'text': '❌ Cancelar cadastro',
                    'callback_data': 'students:create:cancel',
                }
            ],
        ]
    }


def student_address_number_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '🔁 Digitar outro CEP',
                    'callback_data': 'students:create:address:change_zip',
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


def student_field_confirmation_reply_markup() -> dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {
                    'text': '✅ Confirmar',
                    'callback_data': 'students:create:field:confirm',
                },
            ],
            [
                {
                    'text': '✏️ Reescrever',
                    'callback_data': 'students:create:field:rewrite',
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


def student_address_reference_search_actions_rows(
) -> list[list[dict[str, str]]]:
    return [
        [
            {
                'text': '🔎 Pesquisar novamente',
                'callback_data': 'students:create:address:search_again',
            },
        ],
        [
            {
                'text': '🔙 Voltar para opções de endereço',
                'callback_data': 'students:create:address:back',
            },
        ],
        [
            {
                'text': '❌ Cancelar cadastro',
                'callback_data': 'students:create:cancel',
            },
        ],
    ]


def student_edit_address_reference_search_actions_rows(
) -> list[list[dict[str, str]]]:
    return [
        [
            {
                'text': '🔎 Pesquisar novamente',
                'callback_data': 'students:edit:address:search_again',
            },
        ],
        [
            {
                'text': '🔙 Voltar para opções de endereço',
                'callback_data': 'students:edit:address:back',
            },
        ],
        [
            {
                'text': '❌ Cancelar edição',
                'callback_data': 'students:edit:cancel',
            },
        ],
    ]


def student_responsible_reference_search_actions_rows(
) -> list[list[dict[str, str]]]:
    return [
        [
            {
                'text': '🔎 Pesquisar novamente',
                'callback_data': 'students:create:responsible:search_again',
            },
        ],
        [
            {
                'text': '🔙 Voltar para opções de responsável',
                'callback_data': 'students:create:responsible:back',
            },
        ],
        [
            {
                'text': '❌ Cancelar cadastro',
                'callback_data': 'students:create:cancel',
            },
        ],
    ]
