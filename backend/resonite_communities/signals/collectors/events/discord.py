import re
from datetime import datetime

from disnake.ext import commands

from resonite_communities.models import EventStatus
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.signals.collectors.event import EventsCollector

# TODO: The domain should probably be customizable per community
# TODO: Fix the syntax warning
re_location_web_session_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_location_session_url_match_compiled = re.compile('(lnl-nat|res-steam):\/\/([^\s]+)')

class DiscordEventsCollector(EventsCollector, commands.Cog):
    scheduler_type = SignalSchedulerType.DISCORD
    jschema = {
            "$schema":"http://json-schema.org/draft-04/schema#",
            "title":"ApolloConfig",
            "description":"Config for Apollo",
            "type":"object",
            "properties":{
                "community_name": {
                    "description": "The name of the community",
                    "type": "string"
                },
                "community_description": {
                    "description": "The description of a community",
                    "type": "string"
                },
                "community_url": {
                    "description": "The website of the community",
                    "type": "string"
                },
                "tags": {
                    "description": "A list of tags",
                    "type": "array"
                },
                "guild_id":{
                    "description":"The discord guild id of the community",
                    "type": "integer"
                }
            },
            "required":[
                "community_name",
                "community_url",
                "tags",
                "guild_id"
            ]
        }

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

        self.guilds = {}

        if not self.valid_config:
            return

    def update_config(self):
        for bot_config in getattr(self.config.SIGNALS, self.name, []):
            # TODO: I should check and warn for:
            # - We are in a discord community server BUT it's not configured
            # - A community is configured BUT we are not in the discord community server
            for guild_bot in self.config.bot.guilds:
                if bot_config['guild_id'] == guild_bot.id:
                    self.guilds.setdefault(bot_config['guild_id'], {})
                    self.guilds.get(bot_config['guild_id'], {})['bot'] = guild_bot
                    self.guilds[bot_config['guild_id']]['config'] = bot_config


    def get_location_web_session_url(self, description: str):
        location_web_session_url_match = re.search(re_location_web_session_url_match_compiled, description)
        if location_web_session_url_match:
            return location_web_session_url_match.group()
        return ''

    def get_location_session_url(self, description: str):
        location_session_url_match = re.search(re_location_session_url_match_compiled, description)
        if location_session_url_match:
            return location_session_url_match.group()
        return ''

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
        for guild in self.guilds.values():
            events = guild['bot'].scheduled_events

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
                    community_url=guild['config'].community_url,
                    community_name=event.guild.name,
                    community_external_id=event.guild.id,
                    tags=",".join(guild['config'].tags),
                    external_id=event.id,
                    scheduler_type=self.scheduler_type.name,
                    status=EventStatus.READY,
                    created_at_external=event.created_at,
                )

            events_id = [event.id for event in events]
            for local_event in self.model.find(scheduler_type=self.scheduler_type.name, community_external_id=guild['bot'].id):
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
        self.update_config()
        self.init_scheduler()