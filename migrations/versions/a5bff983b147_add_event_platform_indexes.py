"""add_event_platform_indexes

Revision ID: a5bff983b147
Revises: 076de2769b0f
Create Date: 2025-11-01 21:52:30.396161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import fastapi_users_db_sqlalchemy
import resonite_communities


# revision identifiers, used by Alembic.
revision: str = 'a5bff983b147'
down_revision: Union[str, None] = '076de2769b0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add boolean columns for platform and visibility filtering
    op.add_column('event', sa.Column('is_private', sa.Boolean(), nullable=True))
    op.add_column('event', sa.Column('is_resonite', sa.Boolean(), nullable=True))
    op.add_column('event', sa.Column('is_vrchat', sa.Boolean(), nullable=True))
    
    # Backfill data based on existing tags
    # Use raw SQL for case-insensitive pattern matching
    op.execute("""
        UPDATE event
        SET is_private = CASE
            WHEN tags ILIKE '%private%' THEN TRUE
            ELSE FALSE
        END,
        is_resonite = CASE
            WHEN tags ILIKE '%resonite%' THEN TRUE
            ELSE FALSE
        END,
        is_vrchat = CASE
            WHEN tags ILIKE '%vrchat%' THEN TRUE
            ELSE FALSE
        END
    """)
    
    # Set NOT NULL constraint after backfill
    op.alter_column('event', 'is_private', nullable=False)
    op.alter_column('event', 'is_resonite', nullable=False)
    op.alter_column('event', 'is_vrchat', nullable=False)
    
    # Create indexes for frequently queried columns
    op.create_index('ix_event_status', 'event', ['status'])
    op.create_index('ix_event_start_time', 'event', ['start_time'])
    op.create_index('ix_event_end_time', 'event', ['end_time'])
    op.create_index('ix_event_is_private', 'event', ['is_private'])
    op.create_index('ix_event_is_resonite', 'event', ['is_resonite'])
    op.create_index('ix_event_is_vrchat', 'event', ['is_vrchat'])
    
    # Composite index for common query pattern (platform + visibility + status + time)
    op.create_index('ix_event_query_filter', 'event', ['is_resonite', 'is_private', 'status', 'start_time'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_event_query_filter', table_name='event')
    op.drop_index('ix_event_is_vrchat', table_name='event')
    op.drop_index('ix_event_is_resonite', table_name='event')
    op.drop_index('ix_event_is_private', table_name='event')
    op.drop_index('ix_event_end_time', table_name='event')
    op.drop_index('ix_event_start_time', table_name='event')
    op.drop_index('ix_event_status', table_name='event')
    
    # Drop columns
    op.drop_column('event', 'is_vrchat')
    op.drop_column('event', 'is_resonite')
    op.drop_column('event', 'is_private')
