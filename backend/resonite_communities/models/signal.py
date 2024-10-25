from enum import Enum
from datetime import datetime

from sqlmodel import Field, Relationship

from resonite_communities.models.base import BaseModel
from resonite_communities.models.community import Community


class EventStatus(str, Enum):
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
    description: str = Field()
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
    updated_at: datetime = Field()
    name: str | None = Field()