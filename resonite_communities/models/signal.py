from uuid import UUID, uuid4
from datetime import datetime

from sqlmodel import Field, Relationship

from resonite_communities.models.base import BaseModel
from resonite_communities.models.community import Community
from resonite_communities.signals import CEEnum
from sqlalchemy import Column, DateTime


class EventStatus(CEEnum):
    CANCELED = "CANCELED"
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    READY = "READY"
    COMPLETED = "COMPLETED"


class Event(BaseModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    created_at_external: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    updated_at_external: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    external_id: str = Field()
    name: str = Field()
    description: str | None = Field()
    session_image: str  | None = Field()
    location: str | None = Field()
    location_web_session_url: str | None = Field()
    location_session_url: str | None = Field()
    start_time: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    end_time: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    community_id: UUID = Field(foreign_key='community.id')
    community: Community | None = Relationship(back_populates="events")
    tags: str | None = Field()
    external_id: str = Field(unique=True)
    scheduler_type: str = Field()
    status: EventStatus = Field()
    is_private: bool = Field(default=False, index=True)
    is_resonite: bool = Field(default=False, index=True)
    is_vrchat: bool = Field(default=False, index=True)

    @classmethod
    def set_insert_fields(cls, fields_to_update: dict):
        """Set fields that should only be set during insert.
        """
        fields_to_update = super().set_insert_fields(fields_to_update)
        if 'status' not in fields_to_update:
            fields_to_update['status'] = EventStatus.READY
        return fields_to_update

class Stream(BaseModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    name: str = Field()
    start_time: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    end_time: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    community_id: UUID = Field(foreign_key='community.id')
    community: Community | None = Relationship(back_populates="streams")
    external_id: str = Field(unique=True)
    tags: str | None = Field()
    scheduler_type: str = Field()
    status: EventStatus = Field()

    @classmethod
    def set_insert_fields(cls, fields_to_update: dict):
        """Set fields that should only be set during insert.
        """
        fields_to_update = super().set_insert_fields(fields_to_update)
        if 'status' not in fields_to_update:
            fields_to_update['status'] = EventStatus.READY
        return fields_to_update
