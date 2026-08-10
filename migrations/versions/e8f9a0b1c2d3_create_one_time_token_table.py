"""one time token table

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-08-10 16:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'one_time_token',
        sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('purpose', sa.String(length=40), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('public_id', sa.Uuid(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['master_id'],
            ['master.id'],
            name=op.f('fk_one_time_token_master_id_master'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_one_time_token')),
    )
    op.create_index(
        op.f('ix_one_time_token_master_id'),
        'one_time_token',
        ['master_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_one_time_token_public_id'),
        'one_time_token',
        ['public_id'],
        unique=True,
    )
    op.create_index(
        op.f('ix_one_time_token_token'),
        'one_time_token',
        ['token'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_one_time_token_token'), table_name='one_time_token')
    op.drop_index(
        op.f('ix_one_time_token_public_id'),
        table_name='one_time_token',
    )
    op.drop_index(
        op.f('ix_one_time_token_master_id'),
        table_name='one_time_token',
    )
    op.drop_table('one_time_token')
