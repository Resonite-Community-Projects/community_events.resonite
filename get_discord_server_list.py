import os
import toml

from simple_discord import Discord

from utils import Config

discord = Discord(Config.DISCORD_BOT_TOKEN)

guilds = discord.get_guilds()

print('\nList of guilds that the bot is connected to:')

for guild in guilds:
    print(f"{guild['name']}: {guild['id']}")