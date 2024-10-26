from resonite_communities.signals.signal import Signal

from resonite_communities.models.signal import Event

class Collector(Signal):
    jschema = None

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)
        self.model = Event()

    def collect(self):
        self.logger.info('Update events collector')

    def init_scheduler(self):
        # You **must** call this method in your collector __init__ method
        self.logger.info('Events collector ready')
        self.scheduler.add_job(self.collect,'interval', minutes=self.config.REFRESH_INTERVAL)
        self.collect()