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

    def __init__(self, config, services, scheduler):
        super().__init__(config, services, scheduler)

        self.guilds = {}

        if not self.valid_config:
            return

    def update_communities(self):
        super().update_communities()
        # TODO: I should check and warn for:
        # - We are in a discord community server BUT it's not configured
        # - A community is configured BUT we are not in the discord community server
        for guild_bot in self.services.discord.bot.guilds:
            for community in self.communities:
                if community.external_id == str(guild_bot.id):
                    community.monitored = True
                    community.config['bot'] = guild_bot
                    # TODO: Fix this, I should not have to re set all the mandatory fields
                    # TODO: This should also have a fallback to the local configuration if their is no information or the other way around
                    Community.upsert(
                        _filter_field=['external_id', 'platform'],
                        _filter_value=[community.external_id, CommunityPlatform.DISCORD],
                        name=guild_bot.name,
                        monitored=False,
                        external_id=str(guild_bot.id),
                        platform=self.platform,
                        logo=guild_bot.icon.url if guild_bot.icon else "",
                        description=guild_bot.description if guild_bot.description else None,
                        url=community.url if community.url else None,
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
                (local_event_end_time and local_event.end_time > datetime.utcnow()) or
                (not local_event_end_time and local_event.start_time > datetime.utcnow())
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
                    tags=",".join(community.tags),
                    external_id=event.id,
                    scheduler_type=self.scheduler_type.name,
                    status=EventStatus.READY,
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
        self.logger.info('Discord collector bot ready')
        self.update_communities()
        self.init_scheduler()