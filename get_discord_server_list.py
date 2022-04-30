import toml

from discord import Discord

with open('config.toml', 'r') as f:
    config = toml.load(f)

DISCORD_BOT_TOKEN = config['DISCORD_BOT_TOKEN']

discord = Discord(DISCORD_BOT_TOKEN)

guilds = discord.get_guilds()

print('\nList of guilds that the bot is connected to:')

for guild in guilds:
    print(f"{guild['name']}: {guild['id']}")