from resonite_communities.signals import SignalSchedulerType

from resonite_communities.signals.collectors.stream import StreamsCollector

class TwitchStreamsCollector(StreamsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

    def collect(self):
        self.logger.info(f'Update streams collector IN MODULE')

