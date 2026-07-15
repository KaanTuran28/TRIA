"""add composite index on police_unit_history(unit_id, recorded_at)

Revision ID: d1e5f9a0b2c7
Revises: c9d4e8a1f2b3
Create Date: 2026-07-13 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e5f9a0b2c7'
down_revision: Union[str, Sequence[str], None] = 'c9d4e8a1f2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Kapsama boslugu analizinin tarihsel "asof" sorgusu (bkz. coverage.py) her birim icin
    # "bu zamandan once en son ne zaman neredeydi" sorusunu soruyor — bu bilesik indeks olmadan
    # unit_id basina tum recorded_at satirlarini sirlamak gerekir.
    op.create_index(
        'ix_police_unit_history_unit_recorded',
        'police_unit_history',
        ['unit_id', sa.text('recorded_at DESC')],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_police_unit_history_unit_recorded', table_name='police_unit_history')
