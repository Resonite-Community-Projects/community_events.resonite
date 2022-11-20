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

class RedisClient:

    def __init__(self, host='127.0.0.1', port=6379):
        self.client = redis.Redis(host=host, port=port, db=0)

    def get(self, key):
        return self.client.get(key)

    def write(self, key, data, api_ver, community=None, deletion=False, local_communities=[]):
    
        dt_now = datetime.now(timezone.utc)

        old_data = self.get(key)
        updated_data = []
        if old_data:
            updated_data = old_data.decode("utf-8").split('\n')


        if isinstance(data, str):
            data = [data]

        data = list(set(data))

        if community:
            updated_data = [ x for x in updated_data if x.split('`')[ekey[api_ver]["community_name"]] != community ]

        for event in data:
            if event not in updated_data:
                updated_data.append(event)

        if deletion:
            for event in updated_data:
                if event not in data:
                    updated_data.remove(event)

        if local_communities:
            for event in updated_data:
                if event.split('`')[ekey[api_ver]["community_name"]] not in local_communities and event not in data:
                    updated_data.remove(event)

        data = []
        for x in updated_data:
            try:
                if parse(x.split('`')[ekey[api_ver]["end_time"]]).replace(tzinfo=pytz.UTC) > dt_now:
                    data.append(x)
            except dateutil.parser._parser.ParserError:
                continue

        def sorting(key):
            if key:
                return key.split('`')[ekey[api_ver]["start_time"]]
            return ''
        data.sort(key=sorting)

        data = "\n".join(d for d in data if d)
        self.client.set(key, data.encode('utf-8'))

    def update(self, key, event_before, event_after, api_ver):
        print('update data')
        updated_data = self.get(key).decode("utf-8").split('\n')
        if event_before in updated_data and event_after not in updated_data:
            updated_data.remove(event_before)
            updated_data.append(event_after)
            self.write(key, updated_data, api_ver, community=event_after.split('`')[ekey[api_ver]["community_name"]])

    def delete(self, key, new_data, api_ver):
        updated_data = self.get(key).decode("utf-8").split('\n')
        events = [x for x in updated_data if new_data != x]
        self.write(key, events, api_ver, deletion=True)