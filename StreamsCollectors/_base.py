import logging

from flask.logging import default_handler

from utils import Config

formatter = logging.Formatter(
    '[%(asctime)s] [%(module)s] '
    '[%(levelname)s] %(message)s',
    "%Y-%m-%d %H:%M:%S %z"
)

logger = logging.getLogger('community_events')
logger.setLevel(logging.INFO)
logger.addHandler(default_handler)
logger.handlers[0].setFormatter(formatter)


separator = {
    1: {
        'field': '`',
        'event': '\n',
    },
    2: {
        'field': chr(30),
        'event': chr(29),
    }
}
class StreamsCollector:

    def __init__(self, config, sched, rclient):
        self.name = self.__class__.__name__

        self.config = config
        self.sched = sched
        self.rclient = rclient
        self.logger = logger

        self.logger.info(f'Initialise {self.name} streams collector')