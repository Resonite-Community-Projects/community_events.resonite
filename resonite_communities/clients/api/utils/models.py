from pydantic import BaseModel

class CommunityRequest(BaseModel):
    name: str
    external_id: str
    platform: str
    url: str
    tags: str
    description: str
    resetDescription: bool | None = None
    private_role_id: str | None = None
    private_channel_id: str | None = None
    events_url: str | None = None
    selected_community_external_ids: dict | None = None
    resetDescription: dict | None = None
