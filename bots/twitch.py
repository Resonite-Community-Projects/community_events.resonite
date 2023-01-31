import os
import toml
import pytz
import logging
from dateutil.parser import parse

from disnake.ext import commands

from .utils.google import GoogleCalendarAPI
from ._base import Bot

separator = {
    1: {
        'field': '`',
        'event': '\n',
    },
    2: {
        'field': chr(30),
        'event': chr(29),
    }
}


class TwitchBot(Bot):
    jschema = True

    def __init__(self, bot, config, sched, dclient, rclient, tclient, *args, **kwargs):
        super().__init__(bot, config, sched, dclient, rclient)
        self.tclient = tclient
        

    @commands.Cog.listener()
    async def on_ready(self):
        print('twitch bot ready')
        self.sched.add_job(self.get_data, 'interval', args=(self.dclient,), minutes=5)
        await self.get_data(self.dclient)

    async def get_data(self, dclient):
        print('update twitch events')
        print(self.tclient.get_schedules())
        str_streams = []
        streams = self.tclient.get_schedules()
        for stream in streams:
            str_streams.append(f"{separator[2]['field']}".join(stream))
        streams = f"{separator[2]['event']}".join(s for s in str_streams if s)
        print(streams)
        self.rclient.client.set('stream_v2', streams.encode('utf-8'))