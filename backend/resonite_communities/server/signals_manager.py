import asyncio
import os
import disnake
import inspect

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from disnake.ext import commands
import sentry_sdk

from resonite_communities.signals import (
    collectors,
    transmitters,
    SignalSchedulerType,
)
from resonite_communities.utils import (
    RedisClient,
    Config,
    Services,
    TwitchClient,
)

from resonite_communities.utils.logger import get_logger

logger = get_logger('community_events')


# Clients initialization
redis_client = RedisClient(host=os.getenv('REDIS_HOST', 'cache'), port=os.getenv('REDIS_PORT', 6379))
twitch_client = TwitchClient(client_id=Config.Twitch.client_id, secret=Config.Twitch.secret)
discord_client = disnake.Client()

intents = disnake.Intents.all()
bot = disnake.ext.commands.InteractionBot(intents=intents)
ad_bot = disnake.ext.commands.InteractionBot(intents=intents)

from resonite_communities.models.base import engine

from sqlmodel import SQLModel
SQLModel.metadata.create_all(engine)

#signals_queue = asyncio.Queue()

# Scheduler initialization
scheduler = AsyncIOScheduler(daemon=True)

# Register clients
Services.discord.bot = bot
Services.discord.ad_bot = ad_bot #To be removed when removing AD_DISCORD_BOT_TOKEN
Services.discord.client = discord_client
Services.twitch = twitch_client
Services.redis = redis_client

if "SENTRY_DSN" in Config:

    sentry_sdk.init(
        dsn=Config.SENTRY_DSN,
        send_default_pii=True,
        traces_sample_rate=1.0,
    )

async def main():

    # Load collectors
    logger.info('Loading collectors...')
    #return
    for name, obj in inspect.getmembers(collectors, predicate=inspect.isclass):
        signal_collector = obj(Config, Services, scheduler)

        if not signal_collector.valid_config:
            logger.warning(f'Skipping {name} due to invalid configuration.')
            continue

        match signal_collector.scheduler_type:
            case SignalSchedulerType.DISCORD:
                logger.info(f'Setting up {signal_collector.name} collector as Discord bot.')
                bot.add_cog(signal_collector)
                # FIXME: Remove this test when removing AD_DISCORD_BOT_TOKEN
                # Ugly add a cog to a bot with another token
                ad_bot.add_cog(obj(Config, Services, scheduler, True))
            case SignalSchedulerType.APSCHEDULER:
                logger.info(f'Setting up {signal_collector.name} collector as scheduled.')
                signal_collector.init_scheduler()

    # Loading transmitters
    logger.info('Loading transmitters...')
    transmitters_count = 0

    for name, obj in inspect.getmembers(transmitters, predicate=inspect.isclass):
        logger.info(f'Initialization {name} transmitter')
        obj(Config, scheduler, redis_client)

        transmitters_count += 1

    if not transmitters_count:
        logger.warning('No transmitters loaded!')

    # Start scheduler
    logger.info('Starting scheduler...')
    scheduler.start()

    # Stat Discord bot
    logger.info('Starting Discord bots...')
    await asyncio.gather(
        bot.start(Config.DISCORD_BOT_TOKEN),
        ad_bot.start(Config.AD_DISCORD_BOT_TOKEN),
    )

    # End process
    logger.info('Stopping...')

def run():
    asyncio.run(main())