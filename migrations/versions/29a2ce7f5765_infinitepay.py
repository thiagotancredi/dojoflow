"""infinitepay: checkout links, encrypted API key and payment source

Revision ID: 29a2ce7f5765
Revises: c3d4e5f6a7b8
Create Date: 2026-10-24 06:38:29.423284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29a2ce7f5765'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('infinitepay_checkout',
    sa.Column('academy_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('handle', sa.String(length=60), nullable=False),
    sa.Column('order_nsu', sa.String(length=64), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('url', sa.String(length=1000), nullable=False),
    sa.Column('status', sa.Enum('open', 'paid', 'canceled', 'review', 'resolved', name='checkoutstatus', native_enum=False), nullable=False),
    sa.Column('transaction_nsu', sa.String(length=64), nullable=True),
    sa.Column('invoice_slug', sa.String(length=64), nullable=True),
    sa.Column('receipt_url', sa.String(length=500), nullable=True),
    sa.Column('capture_method', sa.String(length=20), nullable=True),
    sa.Column('paid_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('installments', sa.Integer(), nullable=True),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('payment_transaction_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('public_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['academy_id'], ['academy.id'], name=op.f('fk_infinitepay_checkout_academy_id_academy')),
    sa.ForeignKeyConstraint(['payment_transaction_id'], ['payment_transaction.id'], name=op.f('fk_infinitepay_checkout_payment_transaction_id_payment_transaction')),
    sa.ForeignKeyConstraint(['student_id'], ['student.id'], name=op.f('fk_infinitepay_checkout_student_id_student')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_infinitepay_checkout')),
    sa.UniqueConstraint('order_nsu', name=op.f('uq_infinitepay_checkout_order_nsu')),
    sa.UniqueConstraint('transaction_nsu', name=op.f('uq_infinitepay_checkout_transaction_nsu'))
    )
    op.create_index(op.f('ix_infinitepay_checkout_academy_id'), 'infinitepay_checkout', ['academy_id'], unique=False)
    op.create_index(op.f('ix_infinitepay_checkout_payment_transaction_id'), 'infinitepay_checkout', ['payment_transaction_id'], unique=False)
    op.create_index(op.f('ix_infinitepay_checkout_public_id'), 'infinitepay_checkout', ['public_id'], unique=True)
    op.create_index(op.f('ix_infinitepay_checkout_student_id'), 'infinitepay_checkout', ['student_id'], unique=False)
    op.add_column('academy_billing_settings', sa.Column('infinitepay_handle', sa.String(length=60), nullable=True))
    op.add_column('academy_billing_settings', sa.Column('infinitepay_api_key', sa.String(length=500), nullable=True))
    op.add_column('academy_billing_settings', sa.Column('infinitepay_enabled', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('academy_billing_settings', sa.Column('infinitepay_tested_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payment_transaction', sa.Column('source', sa.Enum('manual', 'infinitepay', name='paymentsource', native_enum=False), server_default='manual', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('payment_transaction', 'source')
    op.drop_column('academy_billing_settings', 'infinitepay_tested_at')
    op.drop_column('academy_billing_settings', 'infinitepay_enabled')
    op.drop_column('academy_billing_settings', 'infinitepay_api_key')
    op.drop_column('academy_billing_settings', 'infinitepay_handle')
    op.drop_index(op.f('ix_infinitepay_checkout_student_id'), table_name='infinitepay_checkout')
    op.drop_index(op.f('ix_infinitepay_checkout_public_id'), table_name='infinitepay_checkout')
    op.drop_index(op.f('ix_infinitepay_checkout_payment_transaction_id'), table_name='infinitepay_checkout')
    op.drop_index(op.f('ix_infinitepay_checkout_academy_id'), table_name='infinitepay_checkout')
    op.drop_table('infinitepay_checkout')
