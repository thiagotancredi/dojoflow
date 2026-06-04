"""create student responsible

Revision ID: a1b2c3d4e5f6
Revises: f41b8c2d9a10
Create Date: 2026-06-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f41b8c2d9a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'student_responsible',
        sa.Column('academy_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column(
            'relationship',
            sa.Enum(
                'self',
                'father',
                'mother',
                'grandmother',
                'grandfather',
                'uncle',
                'aunt',
                'brother',
                'sister',
                name='studentresponsiblerelationship',
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('phone_is_whatsapp', sa.Boolean(), nullable=False),
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
            ['academy_id'],
            ['academy.id'],
            name=op.f('fk_student_responsible_academy_id_academy'),
        ),
        sa.ForeignKeyConstraint(
            ['student_id'],
            ['student.id'],
            name=op.f('fk_student_responsible_student_id_student'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_student_responsible')),
    )

    op.create_index(
        op.f('ix_student_responsible_academy_id'),
        'student_responsible',
        ['academy_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_student_responsible_student_id'),
        'student_responsible',
        ['student_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_student_responsible_public_id'),
        'student_responsible',
        ['public_id'],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_student_responsible_public_id'),
        table_name='student_responsible',
    )
    op.drop_index(
        op.f('ix_student_responsible_student_id'),
        table_name='student_responsible',
    )
    op.drop_index(
        op.f('ix_student_responsible_academy_id'),
        table_name='student_responsible',
    )
    op.drop_table('student_responsible')
