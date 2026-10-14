"""add public_id and timestamps to modality

Revision ID: a7b8c9d0e1f2
Revises: f9a0b1c2d3e4
Create Date: 2026-10-13 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('modality', sa.Column('public_id', sa.Uuid(), nullable=True))
    op.execute(
        'UPDATE modality SET public_id = gen_random_uuid() '
        'WHERE public_id IS NULL'
    )
    op.alter_column('modality', 'public_id', nullable=False)
    op.create_index(
        op.f('ix_modality_public_id'),
        'modality',
        ['public_id'],
        unique=True,
    )
    op.add_column(
        'modality',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.add_column(
        'modality',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('modality', 'updated_at')
    op.drop_column('modality', 'created_at')
    op.drop_index(op.f('ix_modality_public_id'), table_name='modality')
    op.drop_column('modality', 'public_id')
