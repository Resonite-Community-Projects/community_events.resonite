from pydantic import BaseModel, field_validator

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

    @field_validator('enabled', mode='before')
    @classmethod
    def validate_enabled(cls, data):
        if isinstance(data, str):
            return data.lower() not in ('false', '0', 'no', 'off', '')
        return data

    @field_validator('resetDescription', mode='before')
    @classmethod
    def validate_reset_description(cls, data):
        if isinstance(data, dict):
            return any(data.values())
        return data
