from resonite_communities.signals.collectors.collector import Collector


class EventsCollector(Collector):

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

        self.config.discord_refresh_interval = self.config['DISCORD_BOT_TOKEN_REFRESH_INTERVAL']

