from resonite_communities.signals.signal import Signal
from resonite_communities.utils.db import async_request_session

class Collector(Signal):

    async def init_scheduler(self):
        # You **must** call this method in your collector __init__ method
        self.logger.info(f'{self.name} scheduler initialization')
        if not self.config.REFRESH_INTERVAL:
            self.logger.warning(f'{self.name} scheduler disabled as no refresh interval configured')
            return

        async def job_with_session():
            async with async_request_session():
                await self.collect()

        job_id = f'{getattr(self, "collector_name", self.name)}_collect'
        self.scheduler.add_job(
            job_with_session, 'interval', minutes=self.config.REFRESH_INTERVAL,
            id=job_id, replace_existing=True,
        )
        await self.collect()