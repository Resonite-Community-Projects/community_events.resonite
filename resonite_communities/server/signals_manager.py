import asyncio
import os
import disnake
import inspect
import argparse
import sys

try:
    import watchfiles
except ImportError:
    watchfiles = None


from apscheduler.schedulers.asyncio import AsyncIOScheduler
from disnake.ext import commands
import sentry_sdk

from resonite_communities.signals import (
    collectors,
    transmitters,
    SignalSchedulerType,
)
from resonite_communities.utils import (
    Config,
    Services,
    TwitchClient,
)

from resonite_communities.utils.logger import get_logger

logger = get_logger('community_events')

if not watchfiles:
    logger.warning("watchfiles not found. --reload option will not be available.")

# Clients initialization
twitch_client = TwitchClient(client_id=Config.Twitch.client_id, secret=Config.Twitch.secret)
discord_client = disnake.Client()

intents = disnake.Intents.all()
bot = disnake.ext.commands.InteractionBot(intents=intents)
ad_bot = disnake.ext.commands.InteractionBot(intents=intents)

# Scheduler initialization
scheduler = AsyncIOScheduler(daemon=True)

# Register clients
Services.discord.bot = bot
Services.discord.ad_bot = ad_bot #To be removed when removing AD_DISCORD_BOT_TOKEN
Services.discord.client = discord_client
Services.twitch = twitch_client

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
        obj(Config, scheduler)

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

def run_without_reload():
    asyncio.run(main())

def run():
    parser = argparse.ArgumentParser(description="Run the signals manager.")
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reloading on file changes (development only)'
    )
    args = parser.parse_args()

    if args.reload:
        if not watchfiles:
            logger.error("watchfiles is required for --reload. Please install it.")
            sys.argv.remove('--reload')
        else:
            logger.info("Starting signals manager with reload enabled...")
        watchfiles.run_process('resonite_communities', target=run_without_reload)
    else:
        run_without_reload()
