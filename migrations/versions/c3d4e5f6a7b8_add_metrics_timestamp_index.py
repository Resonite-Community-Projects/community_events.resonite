"""Add index on metrics.timestamp

Revision ID: c3d4e5f6a7b8
Revises: 9f3a1b6c2e8d
Create Date: 2026-07-04 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = '9f3a1b6c2e8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_metrics_timestamp', 'metrics', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_metrics_timestamp', table_name='metrics')
