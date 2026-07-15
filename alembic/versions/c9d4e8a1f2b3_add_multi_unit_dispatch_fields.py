"""add multi unit dispatch fields to crime_events

Revision ID: c9d4e8a1f2b3
Revises: b7e21f4a9c6d
Create Date: 2026-07-13 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c9d4e8a1f2b3'
down_revision: Union[str, Sequence[str], None] = 'b7e21f4a9c6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'crime_events',
        sa.Column('required_units', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'crime_events',
        sa.Column('assigned_unit_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # Geriye donuk veri: onceden tek-birim atanmis (assigned_unit_id dolu) ama henuz
    # cozulmemis olaylar icin assigned_unit_ids'i doldur — aksi halde yeni coklu-birim
    # sorgusu bu olaylari "hala eksik birim var" sanip 2. bir birim daha atamaya calisir.
    op.execute(
        """
        UPDATE crime_events
        SET assigned_unit_ids = jsonb_build_array(assigned_unit_id)
        WHERE assigned_unit_id IS NOT NULL
          AND resolved_at IS NULL
          AND assigned_unit_ids IS NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('crime_events', 'assigned_unit_ids')
    op.drop_column('crime_events', 'required_units')
