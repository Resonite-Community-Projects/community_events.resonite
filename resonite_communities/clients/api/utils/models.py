from pydantic import BaseModel

class CommunityRequest(BaseModel):
    name: str
    external_id: str
    enabled: bool | None = None
    platform: str
    tags: str | None = None
    languages: str | None = None
    url: str | None = None
    description: str | None = None
    resetDescription: bool | None = None
    private_role_id: str | None = None
    private_channel_id: str | None = None
    community_configurator: str | None = None
    events_url: str | None = None
    selected_community_external_ids: dict | None = None
