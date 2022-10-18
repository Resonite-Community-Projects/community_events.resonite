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
        if not self._filter_neos_event(
            event.name,
            description,
            event.entity_metadata.location,
        ):
            return
        if api_ver == 1:
            event = "{}`{}`{}`{}`{}`{}".format(
                event.name,
                description,
                event.entity_metadata.location,
                event.scheduled_start_time,
                event.scheduled_end_time,
                event.guild.name,
            )
        if api_ver == 2:
            event = "{}`{}`{}`{}`{}`{}`{}`{}".format(
                event.name,
                description,
                event.entity_metadata.location,
                world_session_web_url,
                world_session_url,
                event.scheduled_start_time,
                event.scheduled_end_time,
                event.guild.name,
            )
        return event

    @commands.Cog.listener('on_guild_scheduled_event_create')
    async def on_scheduled_event_create(self, event):
        logging.info('event created in cog')
        self.rclient.write('events_v1', self.format_event(event, 1), api_ver=1)

    @commands.Cog.listener()
    async def on_guild_scheduled_event_delete(self, event):
        logging.info('event delete in cog')
        self.rclient.delete('events_v1', self.format_event(event, 1), api_ver=1)


    @commands.Cog.listener('on_guild_scheduled_event_update')
    async def on_scheduled_event_update(self, event_before, event_after):
        logging.info('event updated in cog')
        self.rclient.update('events_v1', self.format_event(event_before, 1), self.format_event(event_after, 1), api_ver=1)

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('discord bot ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=1)
        await self.get_data(self.dclient)

    async def get_events(self, guild):
        events = guild.scheduled_events
        _events = []
        for event in events:
            _event = self.format_event(event, 1)
            if _event:
                _events.append(_event)
        if _events:
            self.rclient.write('events_v1', _events, api_ver=1, community_overwrite=True)
        _event = self.get_aggregated_events()
        if _event:
            _events.extend(_event)
        if _events:
            self.rclient.write('aggregated_events_v1', _events, api_ver=1, community_overwrite=True)

    async def get_data(self, dclient):
        for guild in self.bot.guilds:
            await self.get_events(guild)
            sleep(1)
