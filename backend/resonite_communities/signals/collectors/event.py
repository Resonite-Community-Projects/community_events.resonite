import re

from resonite_communities.signals.collectors.collector import Collector

# TODO: The domain should probably be customizable per community
# TODO: Fix the syntax warning
re_location_web_session_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_location_session_url_match_compiled = re.compile('(lnl-nat|res-steam):\/\/([^\s]+)')


class EventsCollector(Collector):

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

        self.config.discord_refresh_interval = self.config['DISCORD_BOT_TOKEN_REFRESH_INTERVAL']

    def get_location_web_session_url(self, description: str):
        location_web_session_url_match = re.search(re_location_web_session_url_match_compiled, description)
        if location_web_session_url_match:
            return location_web_session_url_match.group()
        return ''

    def get_location_session_url(self, description: str):
        location_session_url_match = re.search(re_location_session_url_match_compiled, description)
        if location_session_url_match:
            return location_session_url_match.group()
        return ''