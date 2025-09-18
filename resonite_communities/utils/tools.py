import requests

from easydict import EasyDict as edict
import toml
from flask.logging import default_handler

from resonite_communities.utils.text_api import ekey, separator

from resonite_communities.utils.config import ConfigManager

config_manager = ConfigManager()

from resonite_communities.utils.logger import get_logger

logger = get_logger('community_events')

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
                if (event['category'] and event['category']['id'] == self.config.Twitch.game_id) or schedule_data['data']['broadcaster_name'] == Config.Twitch.account_name:
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
    Config = config_manager.infrastructure_config
    public_domains = Config.PUBLIC_DOMAIN
    if not isinstance(public_domains, list):
        public_domains = [public_domains]

    private_domains = Config.PRIVATE_DOMAIN
    if not isinstance(private_domains, list):
        private_domains = [private_domains] if private_domains else []
    if (
        any(domain.endswith(".local") for domain in public_domains) or
        any(domain.endswith(".local") for domain in private_domains)
    ):
        return True
    return False

is_local_env = check_is_local_env()
