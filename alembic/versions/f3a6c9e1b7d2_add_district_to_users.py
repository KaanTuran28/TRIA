"""add district to users

Revision ID: f3a6c9e1b7d2
Revises: e2f4a8b1c3d5
Create Date: 2026-07-16 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a6c9e1b7d2'
down_revision: Union[str, Sequence[str], None] = 'e2f4a8b1c3d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('district', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_district'), 'users', ['district'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_district'), table_name='users')
    op.drop_column('users', 'district')
