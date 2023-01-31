import logging
import re
from jsonschema import validate
import jsonschema

from disnake.ext import commands
import requests

re_location_web_session_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_location_session_url_match_compiled = re.compile('(lnl-nat|neos-steam):\/\/([^\s]+)')
re_location_str_match_compiled = re.compile('Location: (.*)')

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
class EventsCollector(commands.Cog):
    jschema = None

    def __init__(self, bot, config, sched, dclient, rclient, *args, **kwargs):
        self.name = self.__class__.__name__
        if not self.jschema:
            raise ValueError(f"The bot {self.name} must have a declared json schema for its configuration!")

        self.bot = bot
        self.config = config
        self.sched = sched
        self.dclient = dclient
        self.rclient = rclient
        self.logger = logging.getLogger('community_events')

        communities_name = []
        communities_description = []
        for bot in self.config.BOTS.values():
            for config in bot:
                if 'community_name' in config:
                    communities_name.append(config.community_name)
                elif 'communities_name' in config:
                    for community_name in config.communities_name:
                        communities_name.append(community_name)
                self.communities_name = communities_name
                if 'community_description' in config:
                    communities_description.append(config.community_description)
                elif 'communities_description' in config:
                    for community_description in config.communities_description:
                        communities_description.append(community_description)
                self.communities_description = communities_description

        self.guilds = {}
        for bot_config in getattr(self.config.BOTS, self.name, []):
            try:
                validate(instance=bot_config, schema=self.jschema)
            except jsonschema.exceptions.ValidationError as exc:
                self.logger.error(f"Ignoring {self.name} for now. Invalid schema: {exc.message}")
                continue

        self.logger.info(f'Initialise {self.name} events collector')

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

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f'{self.name} events collector ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=5)
        await self.get_data(self.dclient)

    def update_communities(self, communities_name):
        communities_v2 = self.rclient.get('communities_v2')
        if communities_v2:
            communities_v2 = communities_v2.decode("utf-8").split(chr(29))
        else:
            communities_v2 = []
        if isinstance(communities_name, str):
            communities_name = [communities_name]
        for community_name in communities_name:
            communities_v2.append(community_name)
        self.rclient.client.set('communities_v2', "`".join(communities_v2).encode('utf-8'))

    def get_aggregated_events(self, api_ver):
        for server in self.config.SERVERS_EVENT:
            try:
                r = requests.get(server + f'/v{api_ver}/events')
            except Exception as err:
                self.logger.error(f'Error: {err}')
                continue
            if r.status_code != 200:
                self.logger.error(f'Error {r.status_code}: {r.text}')
                continue
            if not r.text:
                self.logger.error(f'Error {r.status_code}: {r}')
                continue
            _server_events = r.text.split(separator[api_ver]['event'])
            return _server_events
        return []

    def sformat(
        self,
        title = '',
        description = '',
        location_str = '',
        session_image = '',
        location_web_session_url = '',
        location_session_url = '',
        start_time = '',
        end_time = '',
        community_name = '',
        community_url = '',
        tags = '',
        api_ver = 0,
    ):
        if api_ver == 1:
            return \
                title + '`' + \
                description + '`' + \
                location_str + '`' + \
                str(start_time) + '`' + \
                str(end_time) + '`' + \
                community_name
        elif api_ver == 2:
            return \
                title + chr(30) + \
                description + chr(30) + \
                session_image + chr(30) + \
                location_str + chr(30) + \
                location_web_session_url + chr(30) + \
                location_session_url + chr(30) + \
                str(start_time) + chr(30) + \
                str(end_time) + chr(30) + \
                community_name + chr(30) + \
                community_url + chr(30) + \
                tags + chr(30) + \
                self.__class__.__name__ # Source
        else:
            raise ValueError(
                'Invalid API version'
            )

    def get_location_web_session_url(self, description):
        location_web_session_url_match = re.search(re_location_web_session_url_match_compiled, description)
        if location_web_session_url_match:
            return location_web_session_url_match.group()
        return ''

    def get_location_session_url(self, description):
        location_session_url_match = re.search(re_location_session_url_match_compiled, description)
        if location_session_url_match:
            return location_session_url_match.group()
        return ''

    def get_location_str(self, description):
        location_str_match = re.search(re_location_str_match_compiled, description)
        if location_str_match:
            return location_str_match.group(1)
        return ''