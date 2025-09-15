"""fix_enum_type_consistency_for_platform_columns

Revision ID: 076de2769b0f
Revises: 8a1785ac21ec
Create Date: 2025-09-14 23:11:45.587945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import fastapi_users_db_sqlalchemy
import resonite_communities


# revision identifiers, used by Alembic.
revision: str = '076de2769b0f'
down_revision: Union[str, None] = '8a1785ac21ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix wrong type
    op.execute("ALTER TABLE community ALTER COLUMN platform_on_remote TYPE communityplatform USING platform_on_remote::text::communityplatform")

    # Convert all TIMESTAMP columns to TIMESTAMPTZ

    # Community table
    op.execute("ALTER TABLE community ALTER COLUMN created_at TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE community ALTER COLUMN updated_at TYPE TIMESTAMPTZ")

    # Event table
    op.execute("ALTER TABLE event ALTER COLUMN created_at TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE event ALTER COLUMN updated_at TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE event ALTER COLUMN created_at_external TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE event ALTER COLUMN updated_at_external TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE event ALTER COLUMN start_time TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE event ALTER COLUMN end_time TYPE TIMESTAMPTZ")

    # Stream table
    op.execute("ALTER TABLE stream ALTER COLUMN created_at TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE stream ALTER COLUMN updated_at TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE stream ALTER COLUMN start_time TYPE TIMESTAMPTZ")
    op.execute("ALTER TABLE stream ALTER COLUMN end_time TYPE TIMESTAMPTZ")

    # Metrics table
    op.execute("ALTER TABLE metrics ALTER COLUMN timestamp TYPE TIMESTAMPTZ")


def downgrade() -> None:
    # Convert all TIMESTAMPTZ columns back to TIMESTAMP

    # Community table
    op.execute("ALTER TABLE community ALTER COLUMN created_at TYPE TIMESTAMP")
    op.execute("ALTER TABLE community ALTER COLUMN updated_at TYPE TIMESTAMP")

    # Event table
    op.execute("ALTER TABLE event ALTER COLUMN created_at TYPE TIMESTAMP")
    op.execute("ALTER TABLE event ALTER COLUMN updated_at TYPE TIMESTAMP")
    op.execute("ALTER TABLE event ALTER COLUMN created_at_external TYPE TIMESTAMP")
    op.execute("ALTER TABLE event ALTER COLUMN updated_at_external TYPE TIMESTAMP")
    op.execute("ALTER TABLE event ALTER COLUMN start_time TYPE TIMESTAMP")
    op.execute("ALTER TABLE event ALTER COLUMN end_time TYPE TIMESTAMP")

    # Stream table
    op.execute("ALTER TABLE stream ALTER COLUMN created_at TYPE TIMESTAMP")
    op.execute("ALTER TABLE stream ALTER COLUMN updated_at TYPE TIMESTAMP")
    op.execute("ALTER TABLE stream ALTER COLUMN start_time TYPE TIMESTAMP")
    op.execute("ALTER TABLE stream ALTER COLUMN end_time TYPE TIMESTAMP")

    # Metrics table
    op.execute("ALTER TABLE metrics ALTER COLUMN timestamp TYPE TIMESTAMP")

    # Reverse fix wrong type
    op.execute("ALTER TABLE community ALTER COLUMN platform_on_remote TYPE VARCHAR USING platform_on_remote::text")
