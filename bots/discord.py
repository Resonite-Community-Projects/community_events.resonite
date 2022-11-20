import re
import logging
from time import sleep
from jsonschema import validate
import jsonschema

import disnake
from disnake.ext import commands
from ._base import Bot

re_world_session_web_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_world_session_url_match_compiled = re.compile('(lnl-nat|neos-steam):\/\/([^\s]+)')

class DiscordScheduledEvents(Bot):
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

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

        self.guilds = {}
        for bot_config in getattr(config.BOTS, self.name, []):
            try:
                validate(instance=bot_config, schema=self.jschema)
            except jsonschema.exceptions.ValidationError as exc:
                logging.error(f"Ignoring {self.name} for now. Invalid schema: {exc.message}")
                continue

            self.guilds[bot_config['guild_id']] = bot_config
            self.update_communities(bot_config.community_name)

    def format_event(self, event, api_ver):
        location_web_session_url = self.get_location_web_session_url(event.description)
        location_session_url = self.get_location_session_url(event.description)
        print(self.guilds)
        if event.image:
            session_image = event.image.url
        else:
            session_image = ''
        community_url = self.guilds[event.guild.id].community_url
        tags = "`".join(self.guilds[event.guild.id].tags)
        description = self._clean_text(event.description)
        if event.entity_metadata:
            location_str = event.entity_metadata.location
        else:
            location_str = ''
        if not self._filter_neos_event(
            event.name,
            description,
            location_str,
        ):
            return
        if api_ver == 1:
            event = self.sformat(
                title = event.name,
                description = description,
                location_str = location_str,
                start_time = event.scheduled_start_time,
                end_time = event.scheduled_end_time,
                community_name = event.guild.name,
                api_ver = 1
            )
        if api_ver == 2:
            event = self.sformat(
                title = event.name,
                description = description,
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

    @commands.Cog.listener('on_guild_scheduled_event_create')
    async def on_scheduled_event_create(self, event):
        logging.info('event created in cog')
        self.rclient.write('events_v1', self.format_event(event, api_ver=1), api_ver=1)
        self.rclient.write('events_v2', self.format_event(event, api_ver=2), api_ver=2)

    @commands.Cog.listener()
    async def on_guild_scheduled_event_delete(self, event):
        logging.error('event delete in cog')
        self.rclient.delete('events_v1', self.format_event(event, api_ver=1), api_ver=1)
        self.rclient.delete('events_v2', self.format_event(event, api_ver=2), api_ver=2)


    @commands.Cog.listener('on_guild_scheduled_event_update')
    async def on_scheduled_event_update(self, event_before, event_after):
        logging.info('event updated in cog')
        self.rclient.update('events_v1', self.format_event(event_before, api_ver=1), self.format_event(event_after, 1), api_ver=1)
        self.rclient.update('events_v2', self.format_event(event_before, api_ver=2), self.format_event(event_after, 2), api_ver=2)

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f'{self.name} bot ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=1)
        await self.get_data(self.dclient)

    async def get_events(self, guild):
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

        self.rclient.write('events_v1', _events_v1, api_ver=1, community=self.guilds[guild.id].community_name)
        self.rclient.write('events_v2', _events_v2, api_ver=2, community=self.guilds[guild.id].community_name)

        _aggregated_events_v1 = self.get_aggregated_events(api_ver=1)
        if _aggregated_events_v1:
            _events_v1.extend(_aggregated_events_v1)
        self.rclient.write('aggregated_events_v1', _events_v1, api_ver=1, local_communities=self.communities_name)

        _aggregated_events_v2 = self.get_aggregated_events(api_ver=2)
        if _aggregated_events_v2:
            _events_v2.extend(_aggregated_events_v2)
        self.rclient.write('aggregated_events_v2', _events_v2, api_ver=2, local_communities=self.communities_name)

    async def get_data(self, dclient):
        print('update discord events')
        for guild in self.bot.guilds:
            if guild.id in self.guilds:
                await self.get_events(guild)
                sleep(1)
