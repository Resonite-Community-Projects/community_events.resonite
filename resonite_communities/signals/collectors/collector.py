from resonite_communities.signals.signal import Signal
class Collector(Signal):

    def collect(self):
        self.logger.info('Update collector')

    def init_scheduler(self):
        # You **must** call this method in your collector __init__ method
        self.logger.info(f'{self.name} scheduler initialization')
        self.scheduler.add_job(self.collect,'interval', minutes=self.config.REFRESH_INTERVAL)
        self.collect()