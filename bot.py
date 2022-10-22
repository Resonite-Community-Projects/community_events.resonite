import os
import toml
import disnake
import inspect
from disnake.ext import commands

import bots
from utils import RedisClient, Config
from discord import Discord

from apscheduler.schedulers.asyncio import AsyncIOScheduler

rclient = RedisClient(host=os.getenv('REDIS_HOST', 'cache'), port=os.getenv('REDIS_PORT', 6379))

dclient = disnake.Client()

intents = disnake.Intents.all()
bot = disnake.ext.commands.InteractionBot(intents=intents)

sched = AsyncIOScheduler(daemon=True)

for name, obj in inspect.getmembers(bots):
    if inspect.isclass(obj):
        bot.add_cog(obj(bot, Config, sched, dclient, rclient))

sched.start()

discord = Discord(Config.DISCORD_BOT_TOKEN)
guilds = discord.get_guilds()
guilds_name = []
for guild in guilds:
    if guild["id"] in Config.DISCORD_GUILDS_WHITELISTED:
        guilds_name.append(guild['name'])

rclient.client.set("communities_v2", "`".join(guilds_name).encode('utf-8'))

bot.run(Config.DISCORD_BOT_TOKEN)
