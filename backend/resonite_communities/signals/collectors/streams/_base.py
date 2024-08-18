from resonite_communities.signals.collectors.collector import Collector

class StreamsCollector(Collector):

    def _validate_jschema(self):
        return True

    def _validate_signal_type(self):
        return True

    def _validate_signals_config(self):
        return True