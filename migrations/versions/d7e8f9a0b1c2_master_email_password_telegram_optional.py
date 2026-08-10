"""master email password telegram optional

Revision ID: d7e8f9a0b1c2
Revises: c2978a738c67
Create Date: 2026-08-10 16:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'c2978a738c67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'master',
        'telegram_user_id',
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.add_column(
        'master',
        sa.Column('email', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'master',
        sa.Column('password_hash', sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f('ix_master_email'),
        'master',
        ['email'],
        unique=True,
    )
    op.create_check_constraint(
        'ck_master_has_telegram_or_email',
        'master',
        'telegram_user_id IS NOT NULL OR email IS NOT NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_master_has_telegram_or_email',
        'master',
        type_='check',
    )
    op.drop_index(op.f('ix_master_email'), table_name='master')
    op.drop_column('master', 'password_hash')
    op.drop_column('master', 'email')
    op.alter_column(
        'master',
        'telegram_user_id',
        existing_type=sa.BigInteger(),
        nullable=False,
    )
