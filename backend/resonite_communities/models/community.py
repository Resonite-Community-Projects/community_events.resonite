from datetime import datetime

from sqlmodel import Field, JSON
from sqlalchemy import Column

from resonite_communities.models.base import BaseModel

class Community(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True)
    created_at: datetime = Field()
    updated_at: datetime | None = Field()
    external_id: str = Field()
    platform: str = Field()
    name: str = Field()
    monitored: bool = Field()
    url: str | None = Field()
    tags: list | None = Field(default=[], sa_column=Column(JSON))
    config: dict | None = Field(default={}, sa_column=Column(JSON))

    class Config:
        arbitrary_types_allowed = True