"""refresh session table

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-10-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'refresh_session',
        sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replaced_by_id', sa.Integer(), nullable=True),
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
            name=op.f('fk_refresh_session_master_id_master'),
        ),
        sa.ForeignKeyConstraint(
            ['replaced_by_id'],
            ['refresh_session.id'],
            name=op.f('fk_refresh_session_replaced_by_id_refresh_session'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_session')),
    )
    op.create_index(
        op.f('ix_refresh_session_master_id'),
        'refresh_session',
        ['master_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_refresh_session_public_id'),
        'refresh_session',
        ['public_id'],
        unique=True,
    )
    op.create_index(
        op.f('ix_refresh_session_replaced_by_id'),
        'refresh_session',
        ['replaced_by_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_refresh_session_token_hash'),
        'refresh_session',
        ['token_hash'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_refresh_session_token_hash'),
        table_name='refresh_session',
    )
    op.drop_index(
        op.f('ix_refresh_session_replaced_by_id'),
        table_name='refresh_session',
    )
    op.drop_index(
        op.f('ix_refresh_session_public_id'),
        table_name='refresh_session',
    )
    op.drop_index(
        op.f('ix_refresh_session_master_id'),
        table_name='refresh_session',
    )
    op.drop_table('refresh_session')
