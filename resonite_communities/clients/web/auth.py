from httpx_oauth.clients.discord import DiscordOAuth2

from resonite_communities.utils.config import ConfigManager

config_manager = ConfigManager()

discord_oauth = DiscordOAuth2(
    client_id=str(config_manager.infrastructure_config.DISCORD_CLIENT_ID),
    client_secret=config_manager.infrastructure_config.DISCORD_SECRET,
    scopes=["identify", "guilds", "guilds.members.read", "email"]
)

oauth_clients = {
    "discord": {
        "client": discord_oauth,
        "redirect_uri": config_manager.infrastructure_config.DISCORD_REDIRECT_URL
    }
}
