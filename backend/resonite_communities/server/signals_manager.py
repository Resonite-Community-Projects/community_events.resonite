import os
import toml
import disnake
import inspect
from disnake.ext import commands

from resonite_communities.signals import (
    collectors,
    transmitters,
)
from resonite_communities.utils import RedisClient, Config, TwitchClient

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

#signals_queue = asyncio.Queue()

sched = AsyncIOScheduler(daemon=True)

Config.bot = bot
Config.clients.discord = dclient
Config.clients.twitch = tclient
Config.clients.redis = rclient

for name, obj in inspect.getmembers(collectors):
    if inspect.isclass(obj):
        signal_collector = obj(Config, sched)
        if not signal_collector.valid_config:
            continue
        match signal_collector.signal_type:
            case 'discord':
                logger.info(f'Adding {signal_collector.name} collector to Discord Cog')
                bot.add_cog(signal_collector)
            case _:
                logger.info(f'Adding {signal_collector.name} collector to scheduler')
                signal_collector.init_scheduler()

for name, obj in inspect.getmembers(transmitters):
    if inspect.isclass(obj):
        logger.info(f'Initialization {name} transmitter')
        obj(Config, sched, rclient)

def run():
    logger.info('Starting scheduler')
    sched.start()
    logger.info('Starting Discord bots')
    bot.run(Config.DISCORD_BOT_TOKEN)
    logger.info('Stopping')
