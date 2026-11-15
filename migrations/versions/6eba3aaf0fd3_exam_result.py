"""exam result on graduation list entries

Revision ID: 6eba3aaf0fd3
Revises: a5c530c1633a
Create Date: 2026-11-15 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6eba3aaf0fd3'
down_revision: Union[str, Sequence[str], None] = 'a5c530c1633a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'graduation_list_entry',
        sa.Column(
            'result',
            sa.Enum(
                'pending',
                'approved',
                'failed',
                name='examresult',
                native_enum=False,
            ),
            server_default='pending',
            nullable=False,
        ),
    )
    op.add_column(
        'graduation_list_entry',
        sa.Column('result_on', sa.Date(), nullable=True),
    )
    op.add_column(
        'enrollment_belt',
        sa.Column('graduation_entry_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f('ix_enrollment_belt_graduation_entry_id'),
        'enrollment_belt',
        ['graduation_entry_id'],
        unique=False,
    )
    op.create_foreign_key(
        op.f('fk_enrollment_belt_graduation_entry_id_graduation_list_entry'),
        'enrollment_belt',
        'graduation_list_entry',
        ['graduation_entry_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f('fk_enrollment_belt_graduation_entry_id_graduation_list_entry'),
        'enrollment_belt',
        type_='foreignkey',
    )
    op.drop_index(
        op.f('ix_enrollment_belt_graduation_entry_id'),
        table_name='enrollment_belt',
    )
    op.drop_column('enrollment_belt', 'graduation_entry_id')
    op.drop_column('graduation_list_entry', 'result_on')
    op.drop_column('graduation_list_entry', 'result')
