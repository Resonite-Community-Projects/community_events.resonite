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

class Community(BaseModel, table=True):
    __table_args__ = (UniqueConstraint("external_id", "platform"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field()
    updated_at: datetime | None = Field()
    external_id: str = Field()
    platform: CommunityPlatform = Field()
    name: str = Field()
    logo: str | None = Field()
    description: str | None = Field()
    monitored: bool = Field()
    url: str | None = Field()
    members_count: int | None = Field(default=0)
    tags: list | None = Field(default=[], sa_column=Column(JSON))
    config: dict | None = Field(default={}, sa_column=Column(EasyDictType, default=easydict.EasyDict()))
    events: list["Event"] = Relationship(back_populates="community")
    streams: list["Stream"] = Relationship(back_populates="community")

    class Config:
        arbitrary_types_allowed = True