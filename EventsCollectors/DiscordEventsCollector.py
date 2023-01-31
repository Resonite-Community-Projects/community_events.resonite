import re
from time import sleep

import disnake
from disnake.ext import commands
from ._base import EventsCollector, separator, ekey

re_world_session_web_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_world_session_url_match_compiled = re.compile('(lnl-nat|neos-steam):\/\/([^\s]+)')

class DiscordEventsCollector(EventsCollector):
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
                "community_description",
                "community_url",
                "tags",
                "guild_id"
            ]
        }

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

        self.other_communities = self.communities_name
        for bot_config in getattr(self.config.BOTS, self.name, []):
            self.guilds[bot_config['guild_id']] = bot_config
            self.update_communities(bot_config.community_name)

    def format_event(self, event, api_ver):
        location_web_session_url = self.get_location_web_session_url(event.description)
        location_session_url = self.get_location_session_url(event.description)
        if event.image:
            session_image = event.image.url
        else:
            session_image = ''
        community_url = self.guilds[event.guild.id].community_url
        tags = "`".join(self.guilds[event.guild.id].tags)
        if event.entity_metadata:
            location_str = event.entity_metadata.location
        else:
            location_str = ''
        if not self._filter_neos_event(
            event.name,
            event.description,
            location_str,
        ):
            return
        if api_ver == 1:
            event = self.sformat(
                title = event.name,
                description = self._clean_text(event.description),
                location_str = location_str,
                start_time = event.scheduled_start_time,
                end_time = event.scheduled_end_time,
                community_name = self.guilds[event.guild.id].community_name,
                api_ver = 1
            )
        if api_ver == 2:
            event = self.sformat(
                title = event.name,
                description = event.description,
                session_image = session_image,
                location_str = location_str,
                location_web_session_url = location_web_session_url,
                location_session_url = location_session_url,
                start_time = event.scheduled_start_time,
                end_time = event.scheduled_end_time,
                community_name = self.guilds[event.guild.id].community_name,
                community_url = community_url,
                tags = tags,
                api_ver = 2
            )
        return event

    async def get_events(self, guild):
        ignored_other_communities = [x for x in self.other_communities if x != guild.name]
        events = guild.scheduled_events
        _events_v1 = []
        _events_v2 = []
        for event in events:
            _event_v1 = self.format_event(event, api_ver=1)
            if _event_v1:
                _events_v1.append(_event_v1)
            _event_v2 = self.format_event(event, api_ver=2)
            if _event_v2:
                _events_v2.append(_event_v2)

        self.rclient.write('events_v1', _events_v1, api_ver=1, other_communities=ignored_other_communities)
        self.rclient.write('events_v2', _events_v2, api_ver=2, other_communities=ignored_other_communities)

        _aggregated_events_v1 = self.get_aggregated_events(api_ver=1)
        #for event in _aggregated_events_v1:
        #    print(event.split(separator[1]['field'])[ekey[1]["community_name"]])
        if _aggregated_events_v1:
            _events_v1.extend(_aggregated_events_v1)
        self.rclient.write('aggregated_events_v1', _events_v1, api_ver=1, other_communities=ignored_other_communities)

        _aggregated_events_v2 = self.get_aggregated_events(api_ver=2)
        if _aggregated_events_v2:
            _events_v2.extend(_aggregated_events_v2)
        self.rclient.write('aggregated_events_v2', _events_v2, api_ver=2, other_communities=ignored_other_communities)

    async def get_data(self, dclient):
        self.logger.info(f'Update {self.name} events collector')
        for guild in self.bot.guilds:
            if guild.id in self.guilds:
                await self.get_events(guild)
                sleep(1)
