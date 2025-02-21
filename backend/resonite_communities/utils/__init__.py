from datetime import datetime, timezone

from dateutil.parser import parse
import dateutil
import requests
import pytz

import redis
from easydict import EasyDict as edict
import toml
from dateutil.parser import parse

from flask.logging import default_handler

from resonite_communities.utils.text_api import ekey, separator


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

from resonite_communities.utils.logger import get_logger

logger = get_logger('community_events')

with open('config.toml', 'r') as f:
    config = toml.load(f)

Config = edict(config)
Config.clients = edict()

communities_name = []
communities_define_multiple_time = []
for bots in Config.SIGNALS.values():
    for bot in bots:
        if 'name' in bot and bot['name'] not in communities_name:
            communities_name.append(bot['name'])
        else:
            if 'name' in bot and bot['name'] not in communities_define_multiple_time:
                communities_define_multiple_time.append(bot['name'])

if communities_define_multiple_time:
    logger.error(f'The following communities have been defined too many time: {communities_define_multiple_time}')
    logger.error('Multiple event source for one community are not supported yet')
    exit()

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

        for event in events:
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
        self.logger = get_logger(self.__class__.__name__)

        self.ready = False

        self._auth()
        self.broadcasters = {}

    def _parse_error(self, response):
        try:
            dict_error = response.json()
            if 'error' not in dict_error.keys() or 'message' not in dict_error.key():
                return f"{response.status_code} - {response.text}"
            return f"{response.status_code} - {dict_error['error']} - {dict_error['message']}"
        except Exception:
            return f"{response.status_code}"

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
            self.ready = True
        else:
            self.logger.error(f"Can't connect to twitch: {self._parse_error(response)}")

    def _get_broadcaster_followers(self, user):
        broadcasters_followers = {}
        if not self.ready:
            return broadcasters_followers
        response = requests.get(
            f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={user}',
            headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
        )
        if response.status_code == 200:
            broadcasters_followers = response.json()
        else:
            self.logger.error(f"Can't connect to twitch: {self._parse_error(response)}")
        return broadcasters_followers

    def get_broadcaster_info(self, streamer):
        broadcaster_info = {}
        if not self.ready:
            return broadcaster_info
        response = requests.get(
            f'https://api.twitch.tv/helix/users?login={streamer.external_id}',
            headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
        )
        if response.status_code == 200:
            users_data = response.json()
            if len(users_data['data']) != 1:
                raise ValueError(f'Too many users found for the external_id {streamer.external_id}')
            broadcaster_info = users_data['data'][0]
            broadcaster_info['followers'] = self._get_broadcaster_followers(users_data['data'][0]['id'])
        else:
            self.logger.error(f"Can't connect to twitch: {self._parse_error(response)}")
        return broadcaster_info

    def get_schedule(self, broadcaster):
        events = []
        if not self.ready:
            return events
        response = requests.get(
            f'https://api.twitch.tv/helix/schedule',
            params={'broadcaster_id': broadcaster['id']},
            headers={'Client-ID': self.client_id, 'Authorization': f"Bearer {self._oauth_token}"}
        )
        if response.status_code == 200:
            schedule_data = response.json()
            for event in schedule_data['data']['segments']:
                if (event['category'] and event['category']['id'] == Config.Twitch.game_id) or schedule_data['data']['broadcaster_name'] == Config.Twitch.account_name:
                    events.append(event)
        else:
            if response.status_code != 404:
                self.logger.error(f"{broadcaster['login']} => Can't connect to twitch: {self._parse_error(response)}")
        return events

    def get_streamers(self):
        streamers = []
        if not self.ready:
            return streamers
        for broadcaster_id in self.broadcasters_info:
            streamers.append([self.broadcasters[broadcaster_id]['login'], str(self.broadcasters[broadcaster_id]['followers']['total']), self.broadcasters[broadcaster_id]['profile_image_url'], self.broadcasters[broadcaster_id]['description']])
        return streamers

Services = edict()
Services.discord = edict()

def check_is_local_env():
    """Check if we are in the development environment based on the local domain."""
    if ".local" in Config.PUBLIC_DOMAIN and ".local" in Config.PRIVATE_DOMAIN:
        return True
    return False

is_local_env = check_is_local_env()