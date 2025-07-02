"""Migrate config

Revision ID: 2ad58984e900
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

import resonite_communities
from resonite_communities.models.community import Community, CommunityPlatform


# revision identifiers, used by Alembic.
revision: str = '2ad58984e900'
down_revision: Union[str, None] = '6a467b98d913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upsert_signal_events(signal, platform):
    community = {
        "name": signal['name'],
        "monitored": False,
        "external_id": str(signal['external_id']),
        "custom_description": signal.get('description', None) if signal.get('description', None) else None,
        "platform": platform,
        "url": signal.get('url', None),
        "tags": ",".join(signal.get('tags', [])),
        "config": signal.get('config', {})
    }
    community = Community.upsert(
        _filter_field=['external_id', 'platform'],
        _filter_value=[community['external_id'], community['platform']],
        **community
    )

def upsert_signal_streams(signal, platform):
    community = {
        "name": signal['name'],
        "monitored": False,
        "external_id": str(signal['external_id']),
        "platform": platform,
        "tags": ",".join(signal.get('tags', [])),
    }
    community = Community.upsert(
        _filter_field=['external_id', 'platform'],
        _filter_value=[community['external_id'], community['platform']],
        **community
    )

def upgrade() -> None:
    with open('config.toml', 'r') as f:
        config = toml.load(f)

    Config = edict(config)
    for signal_type, signal_list in Config.SIGNALS.items():
        match signal_type:
            case "TwitchStreamsCollector":
                print("Adding Twitch communities")
                count = 0
                for signal in signal_list:
                    upsert_signal_streams(signal, CommunityPlatform.TWITCH)
                    count += 1
                print(f"{count} Twitch communities added.")
            case "DiscordEventsCollector":
                print("Adding Discord communities")
                count = 0
                for signal in signal_list:
                    upsert_signal_events(signal, CommunityPlatform.DISCORD)
                    count += 1
                print(f"{count} Discord communities added.")
            case "JSONEventsCollector":
                print("Adding json communities")
                count = 0
                for signal in signal_list:
                    upsert_signal_events(signal, CommunityPlatform.JSON)
                    count += 1
                print(f"{count} JSON communities added.")


def downgrade() -> None:
    op.execute("DELETE FROM event")
    op.execute("DELETE FROM stream")
    op.execute("DELETE FROM community")
