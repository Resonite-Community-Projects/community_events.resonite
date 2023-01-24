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

communities_name = []
communities_define_multiple_time = []
for bots in Config.BOTS.values():
    for bot in bots:
        if bot['community_name'] not in communities_name:
            communities_name.append(bot['community_name'])
        else:
            if bot['community_name'] not in communities_define_multiple_time:
                communities_define_multiple_time.append(bot['community_name'])

if communities_define_multiple_time:
    logging.error(f'The following communities have been defined too many time: {communities_define_multiple_time}')
    logging.error('Multiple event source for one community are not supported yet')
    exit()

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

    def write(self, key, new_events, api_ver, other_communities=[]):
    
        dt_now = datetime.now(timezone.utc)

        old_events = self.get(key)
        if old_events:
            old_events = old_events.decode("utf-8").split(separator[api_ver]['event'])
        else:
            old_events = []

        if isinstance(new_events, str):
            new_events = [new_events]

        old_events = [ x for x in old_events if x.split(separator[api_ver]['field'])[ekey[api_ver]["community_name"]] in other_communities ]

        events = old_events
        for new_event in new_events:
            if new_event not in old_events:
                events.append(new_event)

        for event in events:
            try:
                if parse(event.split(separator[api_ver]['field'])[ekey[api_ver]["end_time"]]).replace(tzinfo=pytz.UTC) < dt_now:
                    events.remove(event)
            except dateutil.parser._parser.ParserError:
                continue


        events = self.sort_events(events, api_ver)
        events = f"{separator[api_ver]['event']}".join(d for d in events if d)
        self.client.set(key, events.encode('utf-8'))

    def sort_events(self, events, api_ver):
        def sorting(key):
            if key:
                return key.split(separator[api_ver]['field'])[ekey[api_ver]["start_time"]]
            return ''
        events.sort(key=sorting)
        return events