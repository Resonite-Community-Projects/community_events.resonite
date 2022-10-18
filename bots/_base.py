import logging
from disnake.ext import commands
import requests

class Bot(commands.Cog):

    def __init__(self, bot, config, sched, dclient, rclient):
        print('initialise discord bot')
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

    def get_aggregated_events(self):
        for server in self.config['SERVERS_EVENT']:
            try:
                r = requests.get(server + '/v1/events')
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