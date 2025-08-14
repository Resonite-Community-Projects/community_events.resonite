from sqlmodel import SQLModel, Field


class AppConfig(SQLModel, table=True):
    __tablename__ = "app_config"

    id: int | None = Field(default=None, primary_key=True)

    discord_bot_token: str = Field()
    ad_discord_bot_token: str = Field()
    refresh_interval: int = Field(default=2)
    cloudvar_resonite_user: str = Field()
    cloudvar_resonite_pass: str = Field()
    cloudvar_base_name: str = Field()
    cloudvar_general_name: str = Field()
    facet_url: str = Field()
    normal_user_login: bool = Field()
    hero_color: str | None = Field()
    title_text: str | None = Field()
    info_text: str | None = Field()
    footer_text: str | None = Field()


class MonitoredDomain(SQLModel, table=True):
    __tablename__ = "monitored_domains"

    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(max_length=255, unique=True)
    status: str = Field(max_length=50)

class TwitchConfig(SQLModel, table=True):
    __tablename__ = "twitch_config"

    id: int | None = Field(default=None, primary_key=True)
    client_id: str = Field()
    secret: str = Field()
    game_id: str = Field()
    account_name: str = Field()
