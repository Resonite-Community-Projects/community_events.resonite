import os
import toml
import disnake
import inspect
from disnake.ext import commands

import EventsCollectors
import StreamsCollectors
from utils import RedisClient, Config, TwitchClient

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask.logging import default_handler


import logging
formatter = logging.Formatter(
    '[%(asctime)s] [%(module)s] '
    '[%(levelname)s] %(message)s',
    "%Y-%m-%d %H:%M:%S %z"
)

logger = logging.getLogger('community_events')
logger.setLevel(logging.INFO)
logger.addHandler(default_handler)
logger.handlers[0].setFormatter(formatter)

rclient = RedisClient(host=os.getenv('REDIS_HOST', 'cache'), port=os.getenv('REDIS_PORT', 6379))
tclient = TwitchClient(client_id=Config.TWITCH_CLIENT_ID, secret=Config.TWITCH_SECRET)
dclient = disnake.Client()

intents = disnake.Intents.all()
bot = disnake.ext.commands.InteractionBot(intents=intents)

sched = AsyncIOScheduler(daemon=True)

for name, obj in inspect.getmembers(EventsCollectors):
    if inspect.isclass(obj):
        bot.add_cog(obj(bot, Config, sched, dclient, rclient))

for name, obj in inspect.getmembers(StreamsCollectors):
    if inspect.isclass(obj):
        obj(Config, sched, rclient, tclient)

sched.start()

bot.run(Config.DISCORD_BOT_TOKEN)
