"""add personnel table

Revision ID: e2f4a8b1c3d5
Revises: d1e5f9a0b2c7
Create Date: 2026-07-16 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f4a8b1c3d5'
down_revision: Union[str, Sequence[str], None] = 'd1e5f9a0b2c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'personnel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('sicil_no', sa.String(), nullable=False),
        sa.Column('rank', sa.String(), nullable=False),
        sa.Column('unit_id', sa.String(), nullable=True),
        sa.Column('shift', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('district', sa.String(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_personnel_id'), 'personnel', ['id'], unique=False)
    op.create_index(op.f('ix_personnel_sicil_no'), 'personnel', ['sicil_no'], unique=True)
    op.create_index(op.f('ix_personnel_unit_id'), 'personnel', ['unit_id'], unique=False)
    op.create_index(op.f('ix_personnel_city'), 'personnel', ['city'], unique=False)
    op.create_index(op.f('ix_personnel_district'), 'personnel', ['district'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_personnel_district'), table_name='personnel')
    op.drop_index(op.f('ix_personnel_city'), table_name='personnel')
    op.drop_index(op.f('ix_personnel_unit_id'), table_name='personnel')
    op.drop_index(op.f('ix_personnel_sicil_no'), table_name='personnel')
    op.drop_index(op.f('ix_personnel_id'), table_name='personnel')
    op.drop_table('personnel')
