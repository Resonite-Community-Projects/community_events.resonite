from resonite_communities.signals.collectors.collector import Collector
from resonite_communities.models.signal import Stream


class StreamsCollector(Collector):

    def __init__(self, config, services, scheduler):
        super().__init__(config, services, scheduler)
        self.model = Stream()

    def _validate_scheduler_type(self):
        return True