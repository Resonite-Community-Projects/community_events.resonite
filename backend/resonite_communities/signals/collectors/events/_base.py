from resonite_communities.signals.collectors.collector import Collector


class EventsCollector(Collector):

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

