"""Add better composite index for event query filter

Revision ID: b4e7f2a1c8d3
Revises: 2616ddbd1242
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4e7f2a1c8d3'
down_revision: Union[str, None] = '8cab0f51a805'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Replace the old composite index (is_resonite, is_private, status, start_time) with one
    # that matches the actual query pattern: is_resonite + is_vrchat + status + start_time.
    # is_private was never filtered in the events endpoint; is_vrchat always is.
    op.drop_index('ix_event_query_filter', table_name='event')
    op.create_index(
        'ix_event_query_filter',
        'event',
        ['is_resonite', 'is_vrchat', 'status', 'start_time'],
    )


def downgrade() -> None:
    op.drop_index('ix_event_query_filter', table_name='event')
    op.create_index(
        'ix_event_query_filter',
        'event',
        ['is_resonite', 'is_private', 'status', 'start_time'],
    )
