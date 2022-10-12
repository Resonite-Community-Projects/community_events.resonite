from operator import itemgetter
from datetime import datetime, timezone
from dateutil.parser import parse
import pytz


import redis

class RedisClient:

    def __init__(self, host='127.0.0.1', port=6379):
        self.client = redis.Redis(host=host, port=port, db=0)

    def get(self, key):
        return self.client.get(key)

    def updated_data(self, key, ver_api):
        dt_now = datetime.now(timezone.utc)
        updated_data = []
        data = self.get(key)
        if data:
            updated_data = data.decode("utf-8").split('\n')
            if ver_api == 1:
                print(updated_data)
                updated_data = [x for x in updated_data if parse(x.split('`')[4]).replace(tzinfo=pytz.UTC) > dt_now]
        if data != updated_data:
            self.write(key, updated_data, ver_api)
        return updated_data

    def write(self, key, data, ver_api):
        def sorting(key):
            if key:
                return key.split('`')[3]
            return ''
        if ver_api == 1:
            data.sort(key=sorting)
        data = "\n".join(d for d in data if d)
        self.client.set(key, data.encode('utf-8'))

    def set(self, key, new_data, ver_api):
        updated_data = self.updated_data(key, ver_api)
        updated = False

        for event in new_data:
            if event not in updated_data:
                updated_data.append(event)
                updated = True
        if updated:
            self.write(key, updated_data, ver_api)

    def update(self, key, event_before, event_after, ver_api):
        updated_data = self.updated_data(key, ver_api)
        if event_before in updated_data and event_after not in updated_data:
            updated_data.remove(event_before)
            updated_data.append(event_after)
            self.write(key, updated_data, ver_api)

    def add(self, key, new_data, ver_api):
        updated_data = self.updated_data(key, ver_api)
        if new_data not in updated_data:
            updated_data.append(new_data)
            self.write(key, updated_data, ver_api)

    def delete(self, key, new_data, ver_api):
        updated_data = self.updated_data(key, ver_api)
        events = [x for x in updated_data if new_data != x]
        self.write(key, events, ver_api)