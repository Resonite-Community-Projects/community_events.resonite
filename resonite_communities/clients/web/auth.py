from httpx_oauth.clients.discord import DiscordOAuth2

from resonite_communities.utils import Config

discord_oauth = DiscordOAuth2(
    client_id=str(Config.Discord.client.id),
    client_secret=Config.Discord.client.secret,
    scopes=["identify", "guilds", "guilds.members.read", "email"]
)

oauth_clients = {
    "discord": {
        "client": discord_oauth,
        "redirect_uri": Config.Discord.client.redirect_uri
    }
}