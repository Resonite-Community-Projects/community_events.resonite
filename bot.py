import os
import toml
import disnake
import inspect
from disnake.ext import commands

import bots
from utils import RedisClient

from apscheduler.schedulers.asyncio import AsyncIOScheduler

with open('config.toml', 'r') as f:
    config = toml.load(f)

DISCORD_BOT_TOKEN = config['DISCORD_BOT_TOKEN']

rclient = RedisClient(host=os.getenv('REDIS_HOST', 'cache'))

dclient = disnake.Client()

intents = disnake.Intents.all()
bot = disnake.ext.commands.InteractionBot(intents=intents)

sched = AsyncIOScheduler(daemon=True)

for name, obj in inspect.getmembers(bots):
    if inspect.isclass(obj):
        bot.add_cog(obj(bot, config, sched, dclient, rclient))

sched.start()

bot.run(DISCORD_BOT_TOKEN)
