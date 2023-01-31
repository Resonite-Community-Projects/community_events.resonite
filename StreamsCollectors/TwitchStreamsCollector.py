import os
import toml
import pytz
import logging
from dateutil.parser import parse

from disnake.ext import commands

from ._base import StreamsCollector

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


class TwitchStreamsCollector(StreamsCollector):

    def __init__(self, config, sched, rclient, tclient):
        super().__init__(config, sched, rclient)
        self.tclient = tclient

        self.logger.info(f'{self.name} streams ready')
        self.sched.add_job(self.get_data, 'interval', args=(), minutes=5)
        self.get_data()

        
    def get_data(self):
        self.logger.info(f'Update {self.name} streams collector')
        str_streams = []
        streams = self.tclient.get_schedules()
        for stream in streams:
            str_streams.append(f"{separator[2]['field']}".join(stream))
        streams = f"{separator[2]['event']}".join(s for s in str_streams if s)
        self.rclient.client.set('stream_v2', streams.encode('utf-8'))