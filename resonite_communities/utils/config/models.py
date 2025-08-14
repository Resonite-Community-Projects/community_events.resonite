from sqlmodel import SQLModel, Field


class AppConfig(SQLModel, table=True):
    __tablename__ = "app_config"

    id: int | None = Field(default=None, primary_key=True)

    initiated: bool | None = Field()
    discord_bot_token: str | None = Field()
    ad_discord_bot_token: str | None = Field()
    refresh_interval: int | None = Field()
    cloudvar_resonite_user: str | None = Field()
    cloudvar_resonite_pass: str | None = Field()
    cloudvar_base_name: str | None = Field()
    cloudvar_general_name: str | None = Field()
    facet_url: str | None = Field()
    normal_user_login: bool | None = Field()
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
