"""Add completed event status

Revision ID: 740f7817910e
Revises: d734a13f111c
Create Date: 2025-03-09 20:07:12.889753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import fastapi_users_db_sqlalchemy
import resonite_communities

from resonite_communities.models.signal import EventStatus

# Based on https://stackoverflow.com/a/70133547

# revision identifiers, used by Alembic.
revision: str = '740f7817910e'
down_revision: Union[str, None] = 'd734a13f111c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

enum_name = EventStatus.mro()[0].__name__.lower()

def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE '{EventStatus.COMPLETED.name}'")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    sql = f"""DELETE FROM pg_enum
        WHERE enumlabel = '{EventStatus.COMPLETED.name}'
        AND enumtypid = (
            SELECT oid FROM pg_type WHERE typname = '{enum_name}'
        )"""
    op.execute(sql)
    # ### end Alembic commands ###
