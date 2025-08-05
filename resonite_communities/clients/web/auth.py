from httpx_oauth.clients.discord import DiscordOAuth2

from resonite_communities.utils.config import ConfigManager
from resonite_communities.auth.db import get_session

Config = ConfigManager(get_session).config()

discord_oauth = DiscordOAuth2(
    client_id=str(Config.DISCORD_CLIENT_ID),
    client_secret=Config.DISCORD_SECRET,
    scopes=["identify", "guilds", "guilds.members.read", "email"]
)

oauth_clients = {
    "discord": {
        "client": discord_oauth,
        "redirect_uri": Config.DISCORD_REDIRECT_URL
    }
}