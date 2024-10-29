from datetime import datetime

from sqlmodel import Field, JSON, Relationship
from sqlalchemy import Column, UniqueConstraint

from resonite_communities.models.base import BaseModel
from resonite_communities.signals import CEEnum


class CommunityPlatform(CEEnum):
    DISCORD = 'DISCORD'
    TWITCH = 'TWITCH'
    JSON = 'JSON'

class Community(BaseModel, table=True):
    __table_args__ = (UniqueConstraint("external_id", "platform"),)
    id: int = Field(primary_key=True)
    created_at: datetime = Field()
    updated_at: datetime | None = Field()
    external_id: str = Field()
    platform: CommunityPlatform = Field()
    name: str = Field()
    monitored: bool = Field()
    url: str | None = Field()
    tags: list | None = Field(default=[], sa_column=Column(JSON))
    config: dict | None = Field(default={}, sa_column=Column(JSON))
    events: list["Event"] = Relationship(back_populates="community")
    streams: list["Stream"] = Relationship(back_populates="community")

    class Config:
        arbitrary_types_allowed = True