"""Migrate config

Revision ID: cf949e08cf67
Revises: 6a467b98d913
Create Date: 2025-07-02 21:34:54.523423

"""
import toml
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import fastapi_users_db_sqlalchemy
from easydict import EasyDict as edict

# revision identifiers, used by Alembic.
revision: str = 'cf949e08cf67'
down_revision: Union[str, None] = '6a467b98d913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:

    op.add_column('community', sa.Column('configured', sa.Boolean(), nullable=True))
    op.execute("UPDATE community SET configured = TRUE")
    op.add_column('community', sa.Column('ad_bot_configured', sa.Boolean(), nullable=True))
    op.execute("UPDATE community SET ad_bot_configured = FALSE")
    op.add_column('user', sa.Column('is_moderator', sa.Boolean(), nullable=True))
    op.add_column('user', sa.Column('is_protected', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'is_protected')
    op.drop_column('user', 'is_moderator')
    op.drop_column('community', 'ad_bot_configured')
    op.drop_column('community', 'configured')