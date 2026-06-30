"""add responsible id to student responsible

Revision ID: 12c8ce06bd65
Revises: 50af6d17cbd8
Create Date: 2026-06-30 05:14:57.043886

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12c8ce06bd65'
down_revision: Union[str, Sequence[str], None] = '50af6d17cbd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'student_responsible',
        sa.Column('responsible_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f('ix_student_responsible_responsible_id'),
        'student_responsible',
        ['responsible_id'],
        unique=False,
    )
    op.create_foreign_key(
        op.f('fk_student_responsible_responsible_id_responsible'),
        'student_responsible',
        'responsible',
        ['responsible_id'],
        ['id'],
    )

    connection = op.get_bind()

    student_responsibles = connection.execute(
        sa.text(
            """
            SELECT
                id,
                academy_id,
                name,
                phone,
                phone_is_whatsapp,
                email
            FROM student_responsible
            WHERE responsible_id IS NULL
            """
        )
    ).mappings().all()

    for student_responsible in student_responsibles:
        responsible_id = connection.execute(
            sa.text(
                """
                INSERT INTO responsible (
                    academy_id,
                    name,
                    phone,
                    phone_is_whatsapp,
                    email,
                    public_id
                )
                VALUES (
                    :academy_id,
                    :name,
                    :phone,
                    :phone_is_whatsapp,
                    :email,
                    :public_id
                )
                RETURNING id
                """
            ),
            {
                'academy_id': student_responsible['academy_id'],
                'name': student_responsible['name'],
                'phone': student_responsible['phone'],
                'phone_is_whatsapp': student_responsible[
                    'phone_is_whatsapp'
                ],
                'email': student_responsible['email'],
                'public_id': str(uuid.uuid4()),
            },
        ).scalar_one()

        connection.execute(
            sa.text(
                """
                UPDATE student_responsible
                SET responsible_id = :responsible_id
                WHERE id = :student_responsible_id
                """
            ),
            {
                'responsible_id': responsible_id,
                'student_responsible_id': student_responsible['id'],
            },
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f('fk_student_responsible_responsible_id_responsible'),
        'student_responsible',
        type_='foreignkey',
    )
    op.drop_index(
        op.f('ix_student_responsible_responsible_id'),
        table_name='student_responsible',
    )
    op.drop_column('student_responsible', 'responsible_id')