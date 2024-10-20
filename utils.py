from operator import itemgetter
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import dateutil
import requests
import pytz
from copy import deepcopy

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

def event_field(event, api_ver, field_name):
    return event.split(separator[api_ver]['field'])[ekey[api_ver][field_name]]

class RedisClient:

    def __init__(self, host='127.0.0.1', port=6379):
        self.client = redis.Redis(host=host, port=port, db=0)

    def get(self, key):
        return self.client.get(key)

    def write(self, key, new_events, api_ver, current_communities=[]):

        dt_now = datetime.now(timezone.utc)

        old_events = self.get(key)
        if old_events:
            old_events = old_events.decode("utf-8").split(separator[api_ver]['event'])
        else:
            old_events = []

        if isinstance(new_events, str):
            new_events = [new_events]

        events = []
        for x in old_events:
            if event_field(x, api_ver, 'community_name') not in current_communities:
                events.append(x)

        for new_event in new_events:
            events.append(new_event)

        for event in deepcopy(events):
            try:
                if parse(event_field(event, api_ver, 'end_time')).replace(tzinfo=pytz.UTC) < dt_now and event in events:
                    events.remove(event)
            except dateutil.parser._parser.ParserError:
                logging.error(f"Error parsing date: {event_field(event, api_ver, 'end_time')} for event: {event}")

        events = self.sort_events(events, api_ver)
        events = f"{separator[api_ver]['event']}".join(d for d in events if d)
        self.client.set(key, events.encode('utf-8'))

    def sort_events(self, events, api_ver):
        def sorting(key):
            if key:
                return event_field(key, api_ver, 'start_time')
            return ''
        events.sort(key=sorting)
        return events

class TwitchClient:

    def __init__(self, client_id, secret):
        self.client_id = client_id
        self.secret = secret

        self._auth()
        self.broadcasters = {}
        self.broadcasters_info = self._get_broadcasters_info()

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

    def _get_broadcaster_followers(self, user):
        broadcasters_followers = {}
        response = requests.get(
            f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={user}',
            headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
        )
        if response.status_code == 200:
            broadcasters_followers = response.json()
        else:
            logger.error(f"Can't connect to Twitch: {response.status_code}")
        return broadcasters_followers

    def _get_broadcasters_info(self):
        broadcasters_info = []
        b = ""
        for user_login in Config.TWITCH_STREAMS:
            b += f"&login={user_login}"
        b = b.lstrip("&")
        try:
            response = requests.get(
                f'https://api.twitch.tv/helix/users?{b}',
                headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
            )
        except AttributeError:
            logger.error("There's an AttributeError being caused in _get_broadcasters_info. Likely missing oauth token. Skipping")
            return
        if response.status_code == 200:
            users_data = response.json()
            for user in users_data['data']:
                broadcasters_info.append(user['id'])
                self.broadcasters[user['id']] = {
                    "profile_image_url": user['profile_image_url'],
                    "login": user["login"],
                    "description": user["description"],
                    "profile_image_url": user["profile_image_url"],
                    "followers": self._get_broadcaster_followers(user['id']),
                }

        else:
            logger.error(f"Can't connect to twitch: {response.status_code}")
        return broadcasters_info

    def get_schedules(self):
        dt_now = datetime.now(timezone.utc)
        events = []
        if not self.broadcasters_info:
            logger.info("We have no broadcasters. Skipping get_schedules")
            return
        for broadcaster_id in self.broadcasters_info:
            response = requests.get(
                f'https://api.twitch.tv/helix/schedule',
                params={'broadcaster_id': broadcaster_id},
                headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
            )
            if response.status_code == 200:
                schedule_data = response.json()
                if not schedule_data['data']['segments']:
                    segments = []
                else:
                    segments = schedule_data['data']['segments']
                for d in segments:
                    if parse((d['start_time'])) > dt_now + timedelta(days=7):
                        continue
                    if (d['category'] and d['category']['id'] == Config.TWITCH_GAME_ID) or schedule_data['data']['broadcaster_name'] == Config.TWITCH_RESONITE_ACCOUNT_NAME:
                        events.append(
                            [d['title'], d['start_time'], d['end_time'], schedule_data['data']['broadcaster_name'], self.broadcasters[broadcaster_id]['profile_image_url']]
                        )
            else:
                logger.error(f"{self.broadcasters[broadcaster_id]['login']} => Can't connect to twitch: {response.status_code}: {response}")
        events = sorted(events, key=lambda x: x[1])
        return events

    def get_streamers(self):
        streamers = []
        for broadcaster_id in self.broadcasters_info:
            streamers.append([self.broadcasters[broadcaster_id]['login'], str(self.broadcasters[broadcaster_id]['followers']['total']), self.broadcasters[broadcaster_id]['profile_image_url'], self.broadcasters[broadcaster_id]['description']])
        return streamers