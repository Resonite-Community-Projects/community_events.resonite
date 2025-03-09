from datetime import datetime

from disnake.ext import commands

from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import EventStatus
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.signals.collectors.event import EventsCollector
from resonite_communities.signals.signal import gen_schema


class DiscordEventsCollector(EventsCollector, commands.Cog):
    scheduler_type = SignalSchedulerType.DISCORD
    platform = CommunityPlatform.DISCORD
    jschema = gen_schema(
        title = "DiscordConfig",
        description = "The discord configuration of a server.",
        property_external_id = "The discord guild id of the Discord server.",
        property_name = "The name of the Discord server.",
        property_description = "The description of the Discord server.",
        property_url = "The invite link of the Discord server.",
        property_tags = "The tags about this Discord server.",
        property_config = "The special configuration of this Discord server.",
        properties_required = [
            "external_id",
            "name",
        ]
    )

    def __init__(self, config, services, scheduler, ad_bot=False):
        self.connected_communities = {}
        self.configured_communities = {}

        # FIXME: Remove this variable when removing AD_DISCORD_BOT_TOKEN
        # Don't forget to also remove the param of the init func
        self.ad_bot = ad_bot
        self.collector_name = f"{self.__class__.__name__}{' AD' if self.ad_bot else ''}"

        super().__init__(config, services, scheduler)

        self.guilds = {}

        if not self.valid_config:
            return

    def check_configured_community(self):

        # FIXME: Simplify this test when removing AD_DISCORD_BOT_TOKEN
        # aka keep only self.services.discord.bot
        if self.ad_bot:
            discord_bot = self.services.discord.ad_bot
        else:
            discord_bot = self.services.discord.bot

        # TODO: I should check and warn for:
        # - We are in a discord community server BUT it's not configured
        # - A community is configured BUT we are not in the discord community server

        self.logger.info(f'------------:: {self.collector_name} ::--------------')
        self.logger.info(':: Connected to the following discord community')
        for guild_bot in discord_bot.guilds:
            self.connected_communities[guild_bot.id] = guild_bot.name
            self.logger.info(f"{guild_bot.name} ({guild_bot.id})")

        if self.connected_communities:
            self.logger.info('')
            self.logger.info(':: Configured discord community:')
            for signal in getattr(self.config.SIGNALS, self.name, []):
                # FIXME: Remove all this test when removing AD_DISCORD_BOT_TOKEN
                # keep only the print + self.configured_commu...
                if self.ad_bot and 'private' in signal.tags:
                    self.logger.info(f"{signal['name']} ({signal['external_id']})")
                    self.configured_communities[signal['external_id']] = signal['name']
                if not self.ad_bot and 'public' in signal.tags:
                    self.logger.info(f"{signal['name']} ({signal['external_id']})")
                    self.configured_communities[signal['external_id']] = signal['name']

            self.logger.info('')
            self.logger.info('')
            self.logger.info('::Community connected but not configured:')
            for connected_community_id, connected_community_name in self.connected_communities.items():
                if connected_community_id not in self.configured_communities.keys():
                    self.logger.info(f"{connected_community_name} ({connected_community_id})")

            self.logger.info('')
            self.logger.info('::Communities configured but not connected:')
            for configured_community_id, configured_community_name in self.configured_communities.items():
                if configured_community_id not in self.connected_communities.keys():
                    self.logger.info(f"{configured_community_name} ({configured_community_id})")
        self.logger.info('------------------------------')

    def update_communities(self):

        # FIXME: Simplify this test when removing AD_DISCORD_BOT_TOKEN
        # aka keep only self.services.discord.bot
        if self.ad_bot:
            discord_bot = self.services.discord.ad_bot
        else:
            discord_bot = self.services.discord.bot

        for guild_bot in discord_bot.guilds:
            for community in self.communities:

                # FIXME: Remove this test when removing AD_DISCORD_BOT_TOKEN
                if self.ad_bot and 'private' not in community.tags.split(','):
                    continue
                elif not self.ad_bot and 'private' in community.tags.split(','):
                    continue

                if community.external_id == str(guild_bot.id):
                    community.monitored = True
                    community.config['bot'] = guild_bot
                    # TODO: This should also have a fallback to the local configuration if their is no information or the other way around
                    Community.update(
                        _filter_field=['external_id', 'platform'],
                        _filter_value=[community.external_id, CommunityPlatform.DISCORD],
                        monitored=community.monitored,
                        logo=guild_bot.icon.url if guild_bot.icon else "",
                        description=guild_bot.description if guild_bot.description else None,
                    )
                    break

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
                (local_event_end_time and local_event.end_time < datetime.utcnow()) or
                (not local_event_end_time and local_event.start_time < datetime.utcnow())
        ):
            return True

    def collect(self):
        self.logger.info('Update events collector')
        self.update_communities()
        for community in self.communities:
            if not community.monitored:
                continue
            events = community.config['bot'].scheduled_events

            # Add or Update events
            for event in events:
                if event.name == '[F.E] Campfire Friday':
                    self.logger.error('------')
                    self.logger.error(event.name)

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

                # We do different check based if a community is public or private
                if 'public' in community.tags.split(','):
                    # We check if the event is private
                    if community.config.get('private_channel_id', None):
                        if community.config['private_channel_id'] == event.channel_id:
                            tags.add('private')
                    # If there is no private events channel id configured we assume this event is public
                    if 'private' not in tags and 'public' not in tags:
                        tags.add('public')
                elif 'private' in community.tags.split(','):
                    # We check if the event is public
                    if community.config.get('public_channel_id', None):
                        if community.config['public_channel_id'] == event.channel_id:
                            tags.add('public')
                    # If there is no public events channel id configured we assume this event is private
                    if 'public' not in tags and 'private' not in tags:
                        tags.add('private')
                else:
                    # We don't assume anything, we log an error and skip all the events of this community
                    self.logger.error(f"Community {community.name} have no tags, skipping all events")
                    self.logger.error(f"Please add 'public' or 'private' tag to this community")
                    break

                self.model.upsert(
                    _filter_field='external_id',
                    _filter_value=event.id,
                    name=event.name,
                    description=event.description,
                    session_image=event.image.url if event.image else None,
                    location=event.entity_metadata.location if event.entity_metadata else None,
                    location_web_session_url=self.get_location_web_session_url(event.description),
                    location_session_url=self.get_location_session_url(event.description),
                    start_time=event.scheduled_start_time,
                    end_time=event.scheduled_end_time,
                    community_id=Community.find(external_id=community.external_id)[0].id,
                    tags=",".join(tags),
                    external_id=event.id,
                    scheduler_type=self.scheduler_type.name,
                    created_at_external=event.created_at,
                )

            events_id = [event.id for event in events]
            for local_event in self.model.find(
                    scheduler_type=self.scheduler_type.name,
                    community_id=Community.find(external_id=community.external_id)[0].id
            ):
                if int(local_event.external_id) not in events_id and self.is_cancel(local_event):
                    self.model.update(
                        _filter_field='external_id',
                        _filter_value=local_event.external_id,
                        status=EventStatus.CANCELED
                    )
        self.logger.info('Update events collector DONE')

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f'Discord collector bot {self.name} ready')
        self.check_configured_community()
        self.update_communities()
        self.init_scheduler()