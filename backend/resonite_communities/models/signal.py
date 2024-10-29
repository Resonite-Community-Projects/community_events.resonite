from datetime import datetime

from sqlmodel import Field, Relationship

from resonite_communities.models.base import BaseModel
from resonite_communities.models.community import Community
from resonite_communities.signals import CEEnum


class EventStatus(CEEnum):
    CANCELED = "CANCELED"
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    READY = "READY"


class Event(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True)
    created_at: datetime = Field()
    updated_at: datetime | None = Field()
    created_at_external: datetime | None = Field()
    updated_at_external: datetime | None = Field()
    external_id: str = Field()
    name: str = Field()
    description: str | None = Field()
    session_image: str  | None = Field()
    location: str | None = Field()
    location_web_session_url: str | None = Field()
    location_session_url: str | None = Field()
    start_time: datetime = Field()
    end_time: datetime | None = Field()
    community_id: int = Field(foreign_key='community.id')
    community: Community | None = Relationship(back_populates="events")
    tags: str | None = Field()
    external_id: str = Field(unique=True)
    scheduler_type: str = Field()
    status: EventStatus = Field()

class Stream(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True)
    created_at: datetime = Field()
    updated_at: datetime | None = Field()
    name: str = Field()
    start_time: datetime = Field()
    end_time: datetime = Field()
    community_id: int = Field(foreign_key='community.id')
    community: Community | None = Relationship(back_populates="streams")
    external_id: str = Field(unique=True)
    tags: str | None = Field()
    scheduler_type: str = Field()
    status: EventStatus = Field()