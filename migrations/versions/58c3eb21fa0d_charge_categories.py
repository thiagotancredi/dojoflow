"""extra charges with categories, pay link amount and graduation token

Revision ID: 58c3eb21fa0d
Revises: 6eba3aaf0fd3
Create Date: 2026-11-16 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c3eb21fa0d'
down_revision: Union[str, Sequence[str], None] = '6eba3aaf0fd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIES = (
    'uniform',
    'equipment',
    'championship',
    'event',
    'federation',
    'private_class',
    'products',
    'other',
)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'payment',
        sa.Column(
            'category',
            sa.Enum(*CATEGORIES, name='chargecategory', native_enum=False),
            nullable=True,
        ),
    )
    # Avulsas ficam fora da regra "uma por matrícula e mês"
    op.drop_index('uq_payment_enrollment_kind_month', table_name='payment')
    op.create_index(
        'uq_payment_enrollment_kind_month',
        'payment',
        ['academy_id', 'enrollment_id', 'kind', 'reference_month'],
        unique=True,
        postgresql_where=sa.text("kind IN ('monthly', 'enrollment_fee')"),
    )

    op.add_column(
        'student',
        sa.Column('pay_amount', sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        'student',
        sa.Column(
            'pay_link_month',
            sa.Date(),
            server_default=sa.text("date_trunc('month', current_date)::date"),
            nullable=False,
        ),
    )
    # O link da graduação já enviado continua valendo: nasce igual ao
    # pay_token de hoje
    op.add_column(
        'student',
        sa.Column('graduation_pay_token', sa.String(length=32), nullable=True),
    )
    op.execute('UPDATE student SET graduation_pay_token = pay_token')
    op.alter_column('student', 'graduation_pay_token', nullable=False)
    op.create_index(
        op.f('ix_student_graduation_pay_token'),
        'student',
        ['graduation_pay_token'],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_student_graduation_pay_token'), table_name='student'
    )
    op.drop_column('student', 'graduation_pay_token')
    op.drop_column('student', 'pay_link_month')
    op.drop_column('student', 'pay_amount')

    op.drop_index('uq_payment_enrollment_kind_month', table_name='payment')
    op.execute("DELETE FROM payment WHERE kind = 'extra'")
    op.create_index(
        'uq_payment_enrollment_kind_month',
        'payment',
        ['academy_id', 'enrollment_id', 'kind', 'reference_month'],
        unique=True,
        postgresql_where=sa.text("kind <> 'graduation'"),
    )
    op.drop_column('payment', 'category')
