"""Add index on community.enabled

Revision ID: 9f3a1b6c2e8d
Revises: b4e7f2a1c8d3
Create Date: 2026-07-04 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f3a1b6c2e8d'
down_revision: Union[str, None] = '2616ddbd1242'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_community_enabled', 'community', ['enabled'])


def downgrade() -> None:
    op.drop_index('ix_community_enabled', table_name='community')
