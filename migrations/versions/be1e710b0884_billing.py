"""billing

Revision ID: be1e710b0884
Revises: f8141ff05ffb
Create Date: 2026-10-21 02:48:41.420797

"""
from datetime import date, datetime
from typing import Sequence, Union
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be1e710b0884'
down_revision: Union[str, Sequence[str], None] = 'f8141ff05ffb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _first_billing_month(today: date) -> tuple[date, date]:
    # (mês atual, mês seguinte), sempre no dia 1
    this_month = today.replace(day=1)
    if this_month.month == 12:
        next_month = date(this_month.year + 1, 1, 1)
    else:
        next_month = date(this_month.year, this_month.month + 1, 1)
    return this_month, next_month


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('academy_billing_settings',
    sa.Column('academy_id', sa.Integer(), nullable=False),
    sa.Column('pix_key', sa.String(length=140), nullable=True),
    sa.Column('recipient_name', sa.String(length=120), nullable=True),
    sa.Column('bank_details', sa.String(length=500), nullable=True),
    sa.Column('message_template', sa.String(length=1000), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('public_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['academy_id'], ['academy.id'], name=op.f('fk_academy_billing_settings_academy_id_academy')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_academy_billing_settings')),
    sa.UniqueConstraint('academy_id', name=op.f('uq_academy_billing_settings_academy_id'))
    )
    op.create_index(op.f('ix_academy_billing_settings_public_id'), 'academy_billing_settings', ['public_id'], unique=True)
    op.add_column('enrollment', sa.Column('billing_start_month', sa.Date(), nullable=True))

    # Cobranças que já existem são mensalidades
    op.add_column('payment', sa.Column('kind', sa.Enum('monthly', 'enrollment_fee', name='paymentkind', native_enum=False), nullable=False, server_default='monthly'))
    op.alter_column('payment', 'kind', server_default=None)

    op.drop_constraint(op.f('uq_payment_academy_enrollment_reference_month'), 'payment', type_='unique')
    op.create_unique_constraint('uq_payment_enrollment_kind_month', 'payment', ['academy_id', 'enrollment_id', 'kind', 'reference_month'])
    op.alter_column('payment_transaction', 'payment_method',
               existing_type=sa.VARCHAR(length=13),
               nullable=True)

    # Matrículas que já existem: a primeira mensalidade automática é o
    # primeiro vencimento igual ou posterior a hoje, para nenhuma nascer
    # atrasada. Sem dia de vencimento, fica nulo (não cobra).
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    this_month, next_month = _first_billing_month(today)
    op.execute(
        sa.text(
            'UPDATE enrollment SET billing_start_month = '
            'CASE WHEN due_day >= :today_day THEN :this_month '
            'ELSE :next_month END '
            'WHERE due_day IS NOT NULL'
        ).bindparams(
            today_day=today.day,
            this_month=this_month,
            next_month=next_month,
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Forma de pagamento volta a ser obrigatória
    op.execute(
        "UPDATE payment_transaction SET payment_method = 'other' "
        'WHERE payment_method IS NULL'
    )
    op.alter_column('payment_transaction', 'payment_method',
               existing_type=sa.VARCHAR(length=13),
               nullable=False)

    # O esquema antigo não tem taxa de matrícula: remove essas cobranças
    op.execute(
        'DELETE FROM payment_allocation WHERE payment_id IN '
        "(SELECT id FROM payment WHERE kind = 'enrollment_fee')"
    )
    op.execute("DELETE FROM payment WHERE kind = 'enrollment_fee'")

    op.drop_constraint('uq_payment_enrollment_kind_month', 'payment', type_='unique')
    op.create_unique_constraint(op.f('uq_payment_academy_enrollment_reference_month'), 'payment', ['academy_id', 'enrollment_id', 'reference_month'])
    op.drop_column('payment', 'kind')
    op.drop_column('enrollment', 'billing_start_month')
    op.drop_index(op.f('ix_academy_billing_settings_public_id'), table_name='academy_billing_settings')
    op.drop_table('academy_billing_settings')
