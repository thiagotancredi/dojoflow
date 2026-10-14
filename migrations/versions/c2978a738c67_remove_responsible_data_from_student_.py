"""remove responsible data from student responsible

Revision ID: c2978a738c67
Revises: 12c8ce06bd65
Create Date: 2026-06-30 05:30:11.779107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2978a738c67'
down_revision: Union[str, Sequence[str], None] = '12c8ce06bd65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'student_responsible',
        'responsible_id',
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_column('student_responsible', 'email')
    op.drop_column('student_responsible', 'phone_is_whatsapp')
    op.drop_column('student_responsible', 'phone')
    op.drop_column('student_responsible', 'name')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'student_responsible',
        sa.Column('name', sa.String(length=120), nullable=True),
    )
    op.add_column(
        'student_responsible',
        sa.Column('phone', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'student_responsible',
        sa.Column('phone_is_whatsapp', sa.Boolean(), nullable=True),
    )
    op.add_column(
        'student_responsible',
        sa.Column('email', sa.String(length=255), nullable=True),
    )

    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE student_responsible AS sr
            SET
                name = r.name,
                phone = r.phone,
                phone_is_whatsapp = r.phone_is_whatsapp,
                email = r.email
            FROM responsible AS r
            WHERE sr.responsible_id = r.id
            """
        )
    )

    op.alter_column(
        'student_responsible',
        'name',
        existing_type=sa.String(length=120),
        nullable=False,
    )
    op.alter_column(
        'student_responsible',
        'phone',
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.alter_column(
        'student_responsible',
        'phone_is_whatsapp',
        existing_type=sa.Boolean(),
        nullable=False,
    )
    op.alter_column(
        'student_responsible',
        'responsible_id',
        existing_type=sa.Integer(),
        nullable=True,
    )