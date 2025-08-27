from uuid import UUID, uuid4
from datetime import datetime

import easydict
from sqlmodel import Field, JSON, Relationship
from sqlalchemy import Column, UniqueConstraint

from resonite_communities.models.types import EasyDictType
from resonite_communities.models.base import BaseModel
from resonite_communities.signals import CEEnum

class CommunityPlatform(CEEnum):
    DISCORD = 'DISCORD'
    TWITCH = 'TWITCH'
    JSON = 'JSON'
    JSON_COMMUNITY_EVENT = 'JSON_COMMUNITY_EVENT'

events_platforms = [CommunityPlatform.DISCORD, CommunityPlatform.JSON, CommunityPlatform.JSON_COMMUNITY_EVENT]
streams_platforms = [CommunityPlatform.TWITCH]

class Community(BaseModel, table=True):
    __table_args__ = (UniqueConstraint("external_id", "platform"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field()
    updated_at: datetime | None = Field()
    external_id: str = Field()
    platform: CommunityPlatform = Field()
    platform_on_remote: CommunityPlatform | None = Field()
    name: str = Field()
    logo: str | None = Field()
    default_description: str | None = Field()
    custom_description: str | None = Field()
    monitored: bool = Field()
    configured: bool | None = Field(default=False)
    ad_bot_configured: bool | None = Field(default=False)
    url: str | None = Field()
    members_count: int | None = Field(default=0)
    tags: str | None = Field()
    config: dict | None = Field(default={}, sa_column=Column(EasyDictType, default=easydict.EasyDict()))
    events: list["Event"] = Relationship(
        back_populates="community",
        sa_relationship_kwargs={
            "cascade": "all, delete",
        },
    )
    streams: list["Stream"] = Relationship(
        back_populates="community",
        sa_relationship_kwargs={
            "cascade": "all, delete",
        },
    )

    class Config:
        arbitrary_types_allowed = True