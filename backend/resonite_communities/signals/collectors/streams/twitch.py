from ._base import StreamsCollector
from ._base import StreamsCollector

class TwitchStreamsCollector(StreamsCollector):

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

    def collect(self):
        self.logger.info(f'Update streams collector IN MODULE')

