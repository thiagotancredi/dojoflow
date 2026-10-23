"""pix payment page: key type, city and student pay token

Revision ID: c3d4e5f6a7b8
Revises: f72609848a9f
Create Date: 2026-10-22 23:00:00.000000

"""
import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'f72609848a9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Chaves já salvas ficam SEM tipo: o mestre escolhe (nunca adivinhar)
    op.add_column(
        'academy_billing_settings',
        sa.Column(
            'pix_key_type',
            sa.Enum(
                'cpf',
                'cnpj',
                'phone',
                'email',
                'random',
                name='pixkeytype',
                native_enum=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        'academy_billing_settings',
        sa.Column('pix_city', sa.String(length=60), nullable=True),
    )

    # Cada aluno existente ganha o seu código de link de pagamento
    op.add_column(
        'student', sa.Column('pay_token', sa.String(length=32), nullable=True)
    )
    connection = op.get_bind()
    student_ids = connection.execute(sa.text('SELECT id FROM student'))
    for (student_id,) in student_ids.fetchall():
        connection.execute(
            sa.text('UPDATE student SET pay_token = :token WHERE id = :id'),
            {'token': secrets.token_urlsafe(16), 'id': student_id},
        )
    op.alter_column('student', 'pay_token', nullable=False)
    op.create_index(
        op.f('ix_student_pay_token'), 'student', ['pay_token'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_student_pay_token'), table_name='student')
    op.drop_column('student', 'pay_token')
    op.drop_column('academy_billing_settings', 'pix_city')
    op.drop_column('academy_billing_settings', 'pix_key_type')
