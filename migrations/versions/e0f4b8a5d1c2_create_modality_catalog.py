"""create modality catalog

Revision ID: e0f4b8a5d1c2
Revises: c24f905e5067
Create Date: 2026-06-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e0f4b8a5d1c2'
down_revision: Union[str, Sequence[str], None] = 'c24f905e5067'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INITIAL_MODALITIES = [
    {'name': 'Taekwondo', 'emoji': '🥋'},
    {'name': 'Kickboxing', 'emoji': '🥊'},
    {'name': 'Jiu-jitsu', 'emoji': '🥋'},
    {'name': 'Muay Thai', 'emoji': '🥊'},
    {'name': 'Capoeira', 'emoji': '🤸'},
    {'name': 'Karatê', 'emoji': '🥋'},
    {'name': 'Judô', 'emoji': '🥋'},
    {'name': 'Boxe', 'emoji': '🥊'},
]


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index('ix_modality_academy_id', table_name='modality')
    op.drop_constraint(
        'fk_modality_academy_id_academy',
        'modality',
        type_='foreignkey',
    )
    op.drop_constraint(
        'uq_modality_academy_id_name',
        'modality',
        type_='unique',
    )

    op.execute('DELETE FROM modality')

    op.drop_column('modality', 'academy_id')
    op.add_column(
        'modality',
        sa.Column('emoji', sa.String(length=10), nullable=False),
    )
    op.add_column(
        'modality',
        sa.Column(
            'is_active',
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )

    op.create_unique_constraint(
        'uq_modality_name',
        'modality',
        ['name'],
    )

    op.create_table(
        'academy_modality',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('academy_id', sa.Integer(), nullable=False),
        sa.Column('modality_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['academy_id'],
            ['academy.id'],
            name=op.f('fk_academy_modality_academy_id_academy'),
        ),
        sa.ForeignKeyConstraint(
            ['modality_id'],
            ['modality.id'],
            name=op.f('fk_academy_modality_modality_id_modality'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_academy_modality')),
        sa.UniqueConstraint(
            'academy_id',
            'modality_id',
            name='uq_academy_modality_academy_id_modality_id',
        ),
    )

    op.create_index(
        op.f('ix_academy_modality_academy_id'),
        'academy_modality',
        ['academy_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_academy_modality_modality_id'),
        'academy_modality',
        ['modality_id'],
        unique=False,
    )

    modality_table = sa.table(
        'modality',
        sa.column('name', sa.String),
        sa.column('emoji', sa.String),
        sa.column('is_active', sa.Boolean),
    )

    op.bulk_insert(
        modality_table,
        [
            {
                'name': modality['name'],
                'emoji': modality['emoji'],
                'is_active': True,
            }
            for modality in INITIAL_MODALITIES
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_academy_modality_modality_id'),
        table_name='academy_modality',
    )
    op.drop_index(
        op.f('ix_academy_modality_academy_id'),
        table_name='academy_modality',
    )
    op.drop_table('academy_modality')

    op.drop_constraint(
        'uq_modality_name',
        'modality',
        type_='unique',
    )

    op.execute('DELETE FROM modality')

    op.drop_column('modality', 'is_active')
    op.drop_column('modality', 'emoji')

    op.add_column(
        'modality',
        sa.Column('academy_id', sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        op.f('fk_modality_academy_id_academy'),
        'modality',
        'academy',
        ['academy_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_modality_academy_id'),
        'modality',
        ['academy_id'],
        unique=False,
    )
    op.create_unique_constraint(
        'uq_modality_academy_id_name',
        'modality',
        ['academy_id', 'name'],
    )
