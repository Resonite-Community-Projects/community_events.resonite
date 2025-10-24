import re
from typing import Any
from datetime import datetime, timezone
import traceback

from disnake.ext import commands
from sqlalchemy import select, func
from sqlmodel import Session

from resonite_communities.utils.db import engine, async_request_session
from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import Event, EventStatus
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.signals.collectors.event import EventsCollector


class DiscordEventsCollector(EventsCollector, commands.Cog):
    scheduler_type = SignalSchedulerType.DISCORD
    platform = CommunityPlatform.DISCORD

    def __init__(self, config, services, scheduler, ad_bot=False):
        self.connected_communities = {}
        self.configured_communities = {}

        # FIXME: Remove this variable when removing AD_DISCORD_BOT_TOKEN
        # Don't forget to also remove the param of the init func
        self.ad_bot = ad_bot
        self.collector_name = f"{self.__class__.__name__}{' AD' if self.ad_bot else ''}"

        super().__init__(config, services, scheduler)

        self.guilds = {}

    async def update_communities(self):

        # FIXME: Simplify this test when removing AD_DISCORD_BOT_TOKEN
        # aka keep only self.services.discord.bot
        if self.ad_bot:
            discord_bot = self.services.discord.ad_bot
        else:
            discord_bot = self.services.discord.bot

        database_communities = {
            c.external_id: c
            for c in await Community.find(platform=CommunityPlatform.DISCORD)
        }

        self.communities = []
        for guild_bot in discord_bot.guilds:
            self.logger.info(f"Updating database community {guild_bot.name} information from Discord.")
            external_id = str(guild_bot.id)
            community = database_communities.get(external_id)

            if community:
                if community.platform_on_remote:
                    continue
                ad_bot_configured = False
                if self.ad_bot and not community.ad_bot_configured:
                        ad_bot_configured = True
                # FIXME: Remove this test when removing AD_DISCORD_BOT_TOKEN
                if self.ad_bot and 'private' not in community.tags.split(','):
                    continue
                elif not self.ad_bot and 'private' in community.tags.split(','):
                    continue

                community.ad_bot_configured = ad_bot_configured

                await Community.update(
                    filters=(
                        (Community.external_id == community.external_id) &
                        (Community.platform == CommunityPlatform.DISCORD) &
                        (Community.platform_on_remote == None)
                    ),
                    monitored=True,
                    configured=community.configured,
                    ad_bot_configured=ad_bot_configured,
                    logo=guild_bot.icon.url if guild_bot.icon else "",
                    default_description=guild_bot.description if guild_bot.description else None,

                )
                community.config["bot"] = guild_bot
                self.communities.append(community)
            else:
                community = await Community.add(
                    platform=CommunityPlatform.DISCORD,
                    external_id=external_id,
                    monitored=False,
                    configured=False,
                    ad_bot_configured=False,
                    name=guild_bot.name,
                    logo=guild_bot.icon.url if guild_bot.icon else "",
                    default_description=guild_bot.description or None,
                    tags="",
                )
                community.config["bot"] = guild_bot
                self.communities.append(community)

    def is_cancel(self, local_event):
        """ Check if an event is considered as canceled.

        Discord never send past or deleted event, but we do still store all of them.
        We need to know if an event is being canceled, for that we check the following parameters:
            - There is an end date AND it's in the future
            - There is no end date AND the start date is in the future
        Any event in the past that are considered as canceled we can't have the information in the
        current process.

        """
        local_event_end_time = getattr(local_event, 'end_time')
        if (
                (local_event_end_time and local_event.end_time < datetime.now(timezone.utc)) or
                (not local_event_end_time and local_event.start_time < datetime.now(timezone.utc))
        ):
            return True

    async def detect_and_handle_duplicates(self, community: Any) -> None:
            """ Detect and handle duplicate events for a given community.

            This function identifies duplicate events in the database based on their
            name, start time, end time, and description. It cancels all but one of the
            duplicate events and updates the session image if necessary.

            Args:
                community (Community): The community object for which duplicate events
                                    are being detected and handled.

            Steps:
                1. Detect duplicate events using a subquery.
                2. Retrieve all duplicate events from the database.
                3. Iterate through the duplicates and:
                    - Keep the first event as the unique one.
                    - Cancel all other duplicates.
                    - Update the session image if available.

            Notes:
                - Relies on SQLAlchemy and SQLModel for database operations.
                - Uses `EventStatus` to filter events that are READY, PENDING, or ACTIVE.
            """

            # Detect all the duplicate events
            duplicate_subquery = (
                select(
                    Event.name,
                    Event.start_time,
                    Event.end_time,
                    Event.description)
                .where(
                    Event.community_id == community.id,
                    Event.status.in_([
                        EventStatus.READY,
                        EventStatus.PENDING,
                        EventStatus.ACTIVE
                    ]),
                )
                .group_by(
                    Event.name,
                    Event.start_time,
                    Event.end_time,
                    Event.description
                )
                .having(func.count() > 1)  # Only include groups with more than one event
            ).subquery()

            # Filter all the duplicate events
            duplicates_query = (
                select(
                    Event.id,
                    Event.name,
                    Event.status,
                    Event.session_image,
                    Event.start_time,
                    Event.end_time,
                    Event.description)
                .where(
                    (Event.name == duplicate_subquery.c.name) &
                    (Event.start_time == duplicate_subquery.c.start_time) &
                    (Event.end_time == duplicate_subquery.c.end_time) &
                    (Event.description == duplicate_subquery.c.description)
                )
                .where(
                    Event.community_id == community.id,
                    Event.status.in_([EventStatus.READY, EventStatus.PENDING, EventStatus.ACTIVE]),
                )
            )

            from resonite_communities.utils.db import get_current_async_session

            session = await get_current_async_session()
            result = await session.execute(duplicates_query)
            duplicate_events = result.mappings().all()

            if not len(duplicate_events):
                return

            self.logger.info(f"Processing {len(duplicate_events)} duplicate events for community {community.id}")

            last_unique_event_identifier = None
            first_duplicate_event = None
            for duplicate_event in duplicate_events:

                # Generate a unique identifier for each event based on its attributes
                unique_event_identifier = f"{duplicate_event['name'].replace('\n', '').replace(' ', '')}_{str(duplicate_event['start_time']).replace('\n', '').replace(' ', '')}_{str(duplicate_event['end_time']).replace('\n', '').replace(' ', '')}_{duplicate_event['description'].replace('\n', '').replace(' ', '')}"

                if last_unique_event_identifier != unique_event_identifier:
                    first_duplicate_event = duplicate_event['id']

                if last_unique_event_identifier != unique_event_identifier:
                    await self.model.update(
                        filters=(
                            (Event.id != first_duplicate_event) &
                            (Event.name == duplicate_event['name']) &
                            (Event.start_time == duplicate_event['start_time']) &
                            (Event.end_time == duplicate_event['end_time']) &
                            (Event.description == duplicate_event['description'])
                        ),
                        status=EventStatus.CANCELED,
                    )

                if duplicate_event['session_image']:
                    await self.model.update(
                        filters=(
                            (Event.name == duplicate_event['name']) &
                            (Event.start_time == duplicate_event['start_time']) &
                            (Event.end_time == duplicate_event['end_time']) &
                            (Event.description == duplicate_event['description'])
                        ),
                        session_image=duplicate_event['session_image'],
                    )

                last_unique_event_identifier = unique_event_identifier

    async def upsert_events(self, events: list[Any], community: Any) -> None:
        """ Process and upsert a list of events for a specific community into the database.

        Categorizes events as 'public' or 'private' based on community configuration,
        and tags them with platform-specific tags like 'resonite' or 'vrchat' based on
        content analysis of event details.

        Extracts metadata from event descriptions using a special format. Metadata lines
        in the descriptions following the pattern '+key:value' are parsed and processed,
        then removed from the final description. Supported metadata fields:

        - '+language:code1,code2,...' - Adds language tags in the format 'lang:code'
        - '+tags:custom_tag' - Adds custom tags directly to the event

        Args:
            events (list[Any]): List of Event objects to be processed and upserted.
            community (Any): Community object these events belong to.

        Note:
            Metadata extraction uses regex pattern '^\\+(.*?):(.*)\\n?' to match lines
            starting with '+' followed by key:value pairs. Matched lines are removed
            from the description after processing.
        """
        for event in events:

            tags = {tag for tag in community.tags.split(',') if tag != 'public' and tag != 'private'}

            #if 'resonite' not in tags and 'vrchat' not in tags:
            # Filter and tag any event with the word `resonite` in either of this 3:
            # title, description or location (either in the metadata or the audio channel)
            if (
                "resonite" in event.name.lower() or
                "resonite" in event.description.lower() or
                (
                    "resonite" in str(event.entity_metadata.location if event.entity_metadata else "").lower() or
                    event.channel_id
                )
            ):
                tags.add('resonite')

            # Filter and tag any event with the word `vrchat` in either of this 3:
            # title, description or location (either in the metadata or the audio channel)
            if (
                "vrchat" in event.name.lower() or
                "vrchat" in event.description.lower() or
                "vrchat" in str(event.entity_metadata.location if event.entity_metadata else "").lower()
            ):
                tags.add('vrchat')

            # Handle public vs private event tagging based on community configuration
            if 'public' in community.tags.split(','):
                # For public communities, check if event is in private channel
                if community.config.get('private_channel_id', None):
                    if community.config['private_channel_id'] == event.channel_id:
                        tags.add('private')
                # Default to 'public' if not explicitly private and not already tagged
                if 'private' not in tags and 'public' not in tags:
                    tags.add('public')

            elif 'private' in community.tags.split(','):
                # For private communities, check if event is in public channel
                if community.config.get('public_channel_id', None):
                    if community.config['public_channel_id'] == event.channel_id:
                        tags.add('public')
                # Default to 'private' if not explicitly public and not already tagged
                if 'public' not in tags and 'private' not in tags:
                    tags.add('private')

            else:
                # No assumption if neither 'public' or 'private' tag detected
                # Log an error and skip all the events of this community
                self.logger.error(f"Community {community.name} have no tags, skipping all events")
                self.logger.error(f"Please add 'public' or 'private' tag to this community")
                break

            # Extract metadata from description
            pattern = r'^\+(.*?):(.*)\n?'
            matches = dict(re.findall(pattern, event.description, re.MULTILINE))
            if 'language' in matches:
                langs = [f'lang:{tag.strip()}' for tag in matches['language'].split(",")]
                for lang in langs:
                    tags.add(lang)
            if 'tags' in matches:
                tags.add(matches['tags'].rstrip())
            description = re.sub(pattern, '', event.description, flags=re.MULTILINE)

            await self.model.upsert(
                _filter_field='external_id',
                _filter_value=str(event.id),
                name=event.name,
                description=description,
                session_image=event.image.url if event.image else None,
                location=event.entity_metadata.location if event.entity_metadata else None,
                location_web_session_url=self.get_location_web_session_url(event.description),
                location_session_url=self.get_location_session_url(event.description),
                start_time=event.scheduled_start_time,
                end_time=event.scheduled_end_time,
                community_id= (await Community.find(external_id=community.external_id))[0].id,
                tags=",".join(tags),
                external_id=str(event.id),
                scheduler_type=self.scheduler_type.name,
                created_at_external=event.created_at,
            )

    async def detect_and_handle_passed_events(self, events: list[Any], community: Any) -> None:
        """ Detect events that are no longer active in the Discord and mark them as completed.

        If an event exists in the database but is not present in Discord events list,
        and passes the cancellation check, it will be marked as COMPLETED.

        Args:
            events (_type_): List of event objects from Discord.
            community (_type_): The community object which events are associated with.
        """
        events_id = {event.id:event for event in events}

        for local_event in await self.model.find(
                scheduler_type=self.scheduler_type.name,
                community_id=(await Community.find(external_id=community.external_id))[0].id,
                status__in=(EventStatus.ACTIVE, EventStatus.READY),
        ):

            # If an event in the database no longer exists in Discord
            # and passes the cancellation check, mark it as COMPLETED
            if int(local_event.external_id) not in events_id and self.is_cancel(local_event):
                await self.model.update(
                    filters=(self.model.external_id == local_event.external_id),
                    status=EventStatus.COMPLETED
                )

    async def collect(self):
        await super().collect()
        async with async_request_session():
            self.logger.info(f'Starting collecting signals')
            await self.update_communities()
            for community in self.communities:
                if not community.configured:
                    self.logger.warning(f'Community {community.name} not configured, skipping')
                    continue

                try:
                    self.logger.info(f'Collecting signals for {community.name}')

                    events = community.config['bot'].scheduled_events

                    await self.upsert_events(events, community)

                    await self.detect_and_handle_passed_events(events, community)

                    await self.detect_and_handle_duplicates(community)
                except Exception as e:
                    self.logger.error(f"Error processing community {community.name}: {str(e)}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    continue

            self.logger.info(f'Finished collecting signals')

    @commands.Cog.listener()
    async def on_ready(self):
        async with async_request_session():
            self.logger.info(f'Discord collector bot {self.name} ready')
            await self.update_communities()
            await self.init_scheduler()
