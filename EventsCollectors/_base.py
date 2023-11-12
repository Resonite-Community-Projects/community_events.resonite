import logging
import re
from jsonschema import validate
import jsonschema

from disnake.ext import commands
import requests

re_location_web_session_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_location_session_url_match_compiled = re.compile('(lnl-nat|res-steam):\/\/([^\s]+)')
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
        self.valide_config = False

        communities_name = []
        communities_description = []
        communities = {}
        for bot in self.config.BOTS.values():
            for config in bot:
                community = {}
                if 'community_name' in config:
                    communities_name.append(config.community_name)
                elif 'communities_name' in config:
                    for community_name in config.communities_name:
                        communities_name.append(community_name)
                if 'community_description' in config:
                    communities_description.append(config.community_description)
                elif 'communities_description' in config:
                    for community_description in config.communities_description:
                        communities_description.append(community_description)

        self.communities_name = communities_name
        self.communities_description = communities_description

        self.guilds = {}

        bots_config = getattr(self.config.BOTS, self.name, [])
        if not bots_config and self.name != 'ExternalEventsCollector':
            self.logger.error(f"Ignoring {self.name} for now. No configuration found.")
            return
        for bot_config in bots_config:
            try:
                validate(instance=bot_config, schema=self.jschema)
                self.valide_config = True
            except jsonschema.exceptions.ValidationError as exc:
                self.logger.error(f"Ignoring {self.name} for now. Invalid schema: {exc.message}")
                return

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

    def _filter_resonite_event(self, title, desc, location):
        q = title + desc + location
        if q:
            q = q.replace(' ', '')
            q = q.lower()
        if 'resonite' in q:
            return True
        return False

    def init_sched(self):
        self.logger.info(f'{self.name} events collector ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=self.config['DISCORD_BOT_TOKEN_REFRESH_INTERVAL'])
        self.update_communities()
        self.get_data(self.dclient)

    @commands.Cog.listener()
    async def on_ready(self):
        self.init_sched()

    def get_updated_communities(self, communities):
        return []

    def update_communities(self):
        communities = []
        for bot in self.config.BOTS.values():
            for bot_config in bot:
                community = {}
                if 'community_name' in bot_config:
                    community["name"] = bot_config.community_name if 'community_name' in bot_config else ''
                    community["description"] = bot_config.community_description if 'community_description' in bot_config else ''
                    community["url"] = bot_config.community_url if 'community_url' in bot_config else ''
                    community["icon"] = bot_config.community_icon if 'community_icon' in bot_config else ''
                    communities.append(community)
        communities = self.get_updated_communities(communities)
        str_communities = []
        for community in communities:
            str_communities.append(f"{separator[2]['field']}".join(list(community.values())))
        communities = f"{separator[2]['event']}".join(s for s in str_communities if s)
        if communities:
            self.rclient.client.set('communities_v2', communities.encode('utf-8'))


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

    def get_external_communities(self, community_name=None):
        external_communities = []
        if community_name:
            external_communities.append(community_name)
        for server in self.config.SERVERS_EVENT:
            try:
                _external_communities = requests.get(server + f'/v2/communities')
                external_communities.extend(_external_communities.text.split('`'))
            except Exception as err:
                self.logger.error(f'Error: {err}')

        return external_communities

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