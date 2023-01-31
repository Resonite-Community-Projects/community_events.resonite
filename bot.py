import os
import toml
import disnake
import inspect
from disnake.ext import commands

import bots
from utils import RedisClient, Config, TwitchClient

from apscheduler.schedulers.asyncio import AsyncIOScheduler

rclient = RedisClient(host=os.getenv('REDIS_HOST', 'cache'), port=os.getenv('REDIS_PORT', 6379))
tclient = TwitchClient(client_id=Config.TWITCH_CLIENT_ID, secret=Config.TWITCH_SECRET)
dclient = disnake.Client()

intents = disnake.Intents.all()
bot = disnake.ext.commands.InteractionBot(intents=intents)

sched = AsyncIOScheduler(daemon=True)

rclient.client.delete("communities_v2")

for name, obj in inspect.getmembers(bots):
    if inspect.isclass(obj):
        bot.add_cog(obj(bot, Config, sched, dclient, rclient, tclient))

sched.start()

bot.run(Config.DISCORD_BOT_TOKEN)
