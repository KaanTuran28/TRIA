"""add district to police_units and crime_events

Revision ID: a3f7c9d2e1b4
Revises: d51073ab7a8f
Create Date: 2026-07-13 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7c9d2e1b4'
down_revision: Union[str, Sequence[str], None] = 'd51073ab7a8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('police_units', sa.Column('district', sa.String(), nullable=True))
    op.create_index(op.f('ix_police_units_district'), 'police_units', ['district'], unique=False)
    op.add_column('crime_events', sa.Column('district', sa.String(), nullable=True))
    op.create_index(op.f('ix_crime_events_district'), 'crime_events', ['district'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_crime_events_district'), table_name='crime_events')
    op.drop_column('crime_events', 'district')
    op.drop_index(op.f('ix_police_units_district'), table_name='police_units')
    op.drop_column('police_units', 'district')
