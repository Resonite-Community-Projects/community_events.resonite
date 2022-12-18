from operator import itemgetter
from datetime import datetime, timezone
from dateutil.parser import parse
import dateutil
import pytz

import logging

import redis
from easydict import EasyDict as edict
import toml

with open('config.toml', 'r') as f:
    config = toml.load(f)

Config = edict(config)

ekey = {
    1: {
        "start_time": 3,
        "end_time": 4,
        "community_name": 5,
    },
    2: {
        "start_time": 6,
        "end_time": 7,
        "community_name": 8
    }
}
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

class RedisClient:

    def __init__(self, host='127.0.0.1', port=6379):
        self.client = redis.Redis(host=host, port=port, db=0)

    def get(self, key):
        return self.client.get(key)

    def write(self, key, new_events, api_ver, communities=[]):
    
        dt_now = datetime.now(timezone.utc)

        old_events = self.get(key)
        if old_events:
            old_events = old_events.decode("utf-8").split(separator[api_ver]['event'])
        else:
            old_events = []

        if isinstance(new_events, str):
            new_events = [new_events]

        old_events = [ x for x in old_events if x.split(separator[api_ver]['field'])[ekey[api_ver]["community_name"]] in communities ]

        events = old_events
        for event in new_events:
            if event not in old_events:
                events.append(event)

        for x in old_events:
            try:
                if parse(x.split(separator[api_ver]['field'])[ekey[api_ver]["end_time"]]).replace(tzinfo=pytz.UTC) < dt_now:
                    old_events.remove(x)
            except dateutil.parser._parser.ParserError:
                continue

        old_events = self.sort_events(old_events, api_ver)
        old_events = f"{separator[api_ver]['event']}".join(d for d in old_events if d)
        self.client.set(key, old_events.encode('utf-8'))

    def sort_events(self, events, api_ver):
        def sorting(key):
            if key:
                return key.split(separator[api_ver]['field'])[ekey[api_ver]["start_time"]]
            return ''
        events.sort(key=sorting)
        return events