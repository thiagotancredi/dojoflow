"""add phone is whatsapp to student

Revision ID: f41b8c2d9a10
Revises: e0f4b8a5d1c2
Create Date: 2026-06-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f41b8c2d9a10'
down_revision: Union[str, Sequence[str], None] = 'e0f4b8a5d1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'student',
        sa.Column(
            'phone_is_whatsapp',
            sa.Boolean(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('student', 'phone_is_whatsapp')
