from datetime import datetime

from disnake.ext import commands

from resonite_communities.models.community import Community
from resonite_communities.models.signal import EventStatus
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.signals.collectors.event import EventsCollector

class DiscordEventsCollector(EventsCollector, commands.Cog):
    scheduler_type = SignalSchedulerType.DISCORD
    jschema = {
            "$schema":"http://json-schema.org/draft-04/schema#",
            "title":"ApolloConfig",
            "description":"Config for Discord",
            "type":"object",
            "properties":{
                "external_id":{
                    "description":"The discord guild id of the community",
                    "type": "integer"
                },
                "name": {
                    "description": "The name of the community",
                    "type": "string"
                },
                "description": {
                    "description": "The description of a community",
                    "type": "string"
                },
                "url": {
                    "description": "The website of the community",
                    "type": "string"
                },
                "tags": {
                    "description": "A list of tags",
                    "type": "array"
                },
                "config": {
                    "description": "Special configuration",
                    "type": "object"
                },
            },
            "required":[
                "external_id",
                "name",
                "url",
                "tags"
            ]
        }

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

        self.guilds = {}

        if not self.valid_config:
            return

    def update_communities(self):
        super().update_communities()
        # TODO: I should check and warn for:
        # - We are in a discord community server BUT it's not configured
        # - A community is configured BUT we are not in the discord community server
        for guild_bot in self.config.bot.guilds:
            for community in self.communities:
                if community.external_id == str(guild_bot.id):
                    community.monitored = True
                    community.config['bot'] = guild_bot
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