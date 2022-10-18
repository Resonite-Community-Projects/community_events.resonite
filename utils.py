from operator import itemgetter
from datetime import datetime, timezone
from dateutil.parser import parse
import pytz

import logging


import redis

class RedisClient:

    def __init__(self, host='127.0.0.1', port=6379):
        self.client = redis.Redis(host=host, port=port, db=0)

    def get(self, key):
        return self.client.get(key)

    def write(self, key, data, api_ver, community_overwrite=False, deletion=False):
        
        dt_now = datetime.now(timezone.utc)
        old_data = self.get(key)
        updated_data = []
        if old_data:
            old_data = old_data.decode("utf-8").split('\n')
            if api_ver == 1:
                updated_data = [ x for x in old_data if parse(x.split('`')[4]).replace(tzinfo=pytz.UTC) > dt_now ]

        if isinstance(data, str):
            data = [data]

        data = list(set(data))

        if community_overwrite and data:
            if api_ver == 1:
                updated_data = [ x for x in updated_data if x.split('`')[5] != data[0].split('`')[5] ]
            
        for event in data:
            if event not in updated_data:
                updated_data.append(event)

        if deletion:
            for event in updated_data:
                if event not in data:
                    updated_data.remove(event)

        def sorting(key):
            if key and api_ver == 1:
                return key.split('`')[3]
            return ''
        if api_ver == 1:
            updated_data.sort(key=sorting)

        updated_data = "\n".join(d for d in updated_data if d)
        self.client.set(key, updated_data.encode('utf-8'))

    def update(self, key, event_before, event_after, api_ver):
        print('update data')
        updated_data = self.get(key).decode("utf-8").split('\n')
        if event_before in updated_data and event_after not in updated_data:
            updated_data.remove(event_before)
            updated_data.append(event_after)
            self.write(key, updated_data, api_ver, community_overwrite=True)

    def delete(self, key, new_data, api_ver):
        updated_data = self.get(key).decode("utf-8").split('\n')
        events = [x for x in updated_data if new_data != x]
        self.write(key, events, api_ver, deletion=True)