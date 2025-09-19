from resonite_communities.signals.signal import Signal
class Collector(Signal):

    async def init_scheduler(self):
        # You **must** call this method in your collector __init__ method
        self.logger.info(f'{self.name} scheduler initialization')
        if not self.config.REFRESH_INTERVAL:
            self.logger.warning(f'{self.name} scheduler disabled as no refresh interval configured')
            return
        self.scheduler.add_job(self.collect,'interval', minutes=self.config.REFRESH_INTERVAL)
        await self.collect()