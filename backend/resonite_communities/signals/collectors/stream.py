from resonite_communities.signals.collectors.collector import Collector
from resonite_communities.models.signal import Stream


class StreamsCollector(Collector):

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)
        self.model = Stream()

    def _validate_jschema(self):
        return True

    def _validate_scheduler_type(self):
        return True

    def _validate_signals_config(self):
        return True