import re
import logging
from time import sleep

import disnake
from disnake.ext import commands
from ._base import Bot

re_world_session_web_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_world_session_url_match_compiled = re.compile('(lnl-nat|neos-steam):\/\/([^\s]+)')

class DiscordScheduledEvents(Bot):

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

    def format_event(self, event, api_ver):
        world_session_web_url = ''
        world_session_web_url_match = re.search(re_world_session_web_url_match_compiled, event.description)
        if world_session_web_url_match:
            world_session_web_url = world_session_web_url_match.group()
        world_session_url = ''
        world_session_url_match = re.search(re_world_session_url_match_compiled, event.description)
        if world_session_url_match:
            world_session_url = world_session_url_match.group()
        description = self._clean_text(event.description)
        location_web_url = ''
        location_session_url = ''
        discord_url = ''
        if not self._filter_neos_event(
            event.name,
            description,
            event.entity_metadata.location,
        ):
            return
        if api_ver == 1:
            event = self.sformat(
                title = event.name,
                description = description,
                location_str = event.entity_metadata.location,
                start_time = event.scheduled_start_time,
                end_time = event.scheduled_end_time,
                community_name = event.guild.name,
                api_ver = 1
            )
        if api_ver == 2:
            event = self.sformat(
                title = event.name,
                description = description,
                location_str = event.entity_metadata.location,
                location_web_url = location_web_url,
                location_session_url = location_session_url,
                start_time = event.scheduled_start_time,
                end_time = event.scheduled_end_time,
                community_name = event.guild.name,
                community_url = discord_url,
                api_ver = 2
            )
        return event

    @commands.Cog.listener('on_guild_scheduled_event_create')
    async def on_scheduled_event_create(self, event):
        logging.info('event created in cog')
        self.rclient.write('events_v1', self.format_event(event, 1), api_ver=1)
        self.rclient.write('events_v2', self.format_event(event, 2), api_ver=2)

    @commands.Cog.listener()
    async def on_guild_scheduled_event_delete(self, event):
        logging.info('event delete in cog')
        self.rclient.delete('events_v1', self.format_event(event, 1), api_ver=1)
        self.rclient.write('events_v2', self.format_event(event, 2), api_ver=2)


    @commands.Cog.listener('on_guild_scheduled_event_update')
    async def on_scheduled_event_update(self, event_before, event_after):
        logging.info('event updated in cog')
        self.rclient.update('events_v1', self.format_event(event_before, 1), self.format_event(event_after, 1), api_ver=1)
        self.rclient.update('events_v2', self.format_event(event_before, 2), self.format_event(event_after, 2), api_ver=2)

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('discord bot ready')
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

        self.rclient.write('events_v1', _events_v1, api_ver=1, community=guild.name)
        self.rclient.write('events_v2', _events_v2, api_ver=2, community=guild.name)

        _aggregated_events_v1 = self.get_aggregated_events(api_ver=1)
        if _aggregated_events_v1:
            _events_v1.extend(_aggregated_events_v1)
        self.rclient.write('aggregated_events_v1', _events_v1, api_ver=1, local_communities=self.bot.guilds)

        _aggregated_events_v2 = self.get_aggregated_events(api_ver=2)
        if _aggregated_events_v2:
            _events_v2.extend(_aggregated_events_v2)
        self.rclient.write('aggregated_events_v2', _events_v2, api_ver=2, local_communities=self.bot.guilds)

    async def get_data(self, dclient):
        print('update discord events')
        for guild in self.bot.guilds:
            await self.get_events(guild)
            sleep(1)
