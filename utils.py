from operator import itemgetter
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import dateutil
import requests
import pytz

import logging

import redis
from easydict import EasyDict as edict
import toml
from dateutil.parser import parse

from flask.logging import default_handler


import logging
formatter = logging.Formatter(
    '[%(asctime)s] [%(module)s] '
    '[%(levelname)s] %(message)s',
    "%Y-%m-%d %H:%M:%S %z"
)

logger = logging.getLogger('community_events')
logger.setLevel(logging.INFO)
logger.addHandler(default_handler)
logger.handlers[0].setFormatter(formatter)

with open('config.toml', 'r') as f:
    config = toml.load(f)

Config = edict(config)

communities_name = []
communities_define_multiple_time = []
for bots in Config.BOTS.values():
    for bot in bots:
        if 'community_name' in bot and bot['community_name'] not in communities_name:
            communities_name.append(bot['community_name'])
        else:
            if 'community_name' in bot and bot['community_name'] not in communities_define_multiple_time:
                communities_define_multiple_time.append(bot['community_name'])

if communities_define_multiple_time:
    logger.error(f'The following communities have been defined too many time: {communities_define_multiple_time}')
    logger.error('Multiple event source for one community are not supported yet')
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

class TwitchClient:

    def __init__(self, client_id, secret):
        self.client_id = client_id
        self.secret = secret

        self._auth()
        self.broadcasters = {}
        self.broadcasters_id = self._get_broadcasters_id()

    def _auth(self):
        response = requests.post(
            f'https://id.twitch.tv/oauth2/token',
            params={
                'client_id': self.client_id,
                'client_secret': self.secret,
                'grant_type': 'client_credentials'
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        if response.status_code == 200:
            auth_data = response.json()
            self._oauth_token = auth_data['access_token']
            self._oauth_token_expire_in = auth_data['expires_in'] # use this later
        else:
            logger.error(f"Can't connect to twitch: {response.status_code}")

    def _get_broadcasters_id(self):
        broadcasters_id = []
        user_logins = ['neosvr', 'contactsplus', 'creatorjam', 'raithsphere', 'xlinka', 'zairawolfe']
        b = ""
        for user_login in user_logins:
            b += f"&login={user_login}"
        b = b.lstrip("&")
        response = requests.get(
            f'https://api.twitch.tv/helix/users?{b}',
            headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
        )
        if response.status_code == 200:
            users_data = response.json()
            for user in users_data['data']:
                broadcasters_id.append(user['id'])
                self.broadcasters[user['id']] = {
                    "profile_image_url": user['profile_image_url'],
                    "login": user["login"]
                }

        else:
            logger.error(f"Can't connect to twitch: {response.status_code}")
        return broadcasters_id
    
    def get_schedules(self):
        dt_now = datetime.now(timezone.utc)
        events = []
        for broadcaster_id in self.broadcasters_id:
            response = requests.get(
                f'https://api.twitch.tv/helix/schedule',
                params={'broadcaster_id': broadcaster_id},
                headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
            )
            if response.status_code == 200:
                schedule_data = response.json()
                for d in schedule_data['data']['segments']:
                    if parse((d['start_time'])) > dt_now + timedelta(days=7):
                        continue
                    if (d['category'] and d['category']['id'] == '945792190') or schedule_data['data']['broadcaster_name'] == 'NeosVR':
                        events.append(
                            [d['title'], d['start_time'], d['end_time'], schedule_data['data']['broadcaster_name'], self.broadcasters[broadcaster_id]['profile_image_url']]
                        )
            else:
                logger.error(f"{self.broadcasters[broadcaster_id]['login']} => Can't connect to twitch: {response.status_code}: {response}")
        events = sorted(events, key=lambda x: x[1])
        return events