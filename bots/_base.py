import logging
from disnake.ext import commands
import requests

class Bot(commands.Cog):

    def __init__(self, bot, config, sched, dclient, rclient):
        print(f'initialise {self.__class__.__name__} bot')
        self.bot = bot
        self.config = config
        self.sched = sched
        self.dclient = dclient
        self.rclient = rclient

    def _clean_text(self, text):
        if text:
            text = text.replace('`', ' ')
            text = text.replace('\n\n', ' ')
            text = text.replace('\n\r', ' ')
            text = text.replace('\n', ' ')
            text = text.replace('\r', ' ')
        else:
            text = ''
        return text

    def _filter_neos_event(self, title, desc, location):
        q = title + desc + location
        if q:
            q = q.replace(' ', '')
            q = q.lower()
        if 'neosvr' in q:
            return True
        return False

    def get_aggregated_events(self, api_ver):
        for server in self.config.SERVERS_EVENT:
            try:
                r = requests.get(server + f'/v{api_ver}/events')
            except Exception as err:
                logging.error(f'Error: {err}')
                continue
            if r.status_code != 200:
                logging.error(f'Error {r.status_code}: {r.text}')
                continue
            if not r.text:
                continue
            _server_events = r.text.split('\n')
            return _server_events
        return []

    def sformat(
        self,
        title = '',
        description = '',
        location_str = '',
        location_web_url = '',
        location_session_url = '',
        start_time = '',
        end_time = '',
        community_name = '',
        community_url = '',
        api_ver = 0,
    ):
        if api_ver == 1:
            return "{}`{}`{}`{}`{}`{}".format(
                title,
                description,
                location_str,
                start_time,
                end_time,
                community_name,
            )
        elif api_ver == 2:
            return "{}`{}`{}`{}`{}`{}`{}`{}`{}".format(
                title,
                description,
                location_str,
                location_web_url,
                location_session_url,
                start_time,
                end_time,
                community_name,
                community_url,
                self.__class__.__name__ # Source
            )
        else:
            raise ValueError(
                'Invalid API version'
            )