from gunicorn.app.base import BaseApplication
from resonite_communities.utils.logger import get_logger

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.app = app
        super().__init__()
        logger = get_logger(self.__class__.__name__)
        worker_count = self.options.get('workers', 'unknown')
        logger.info(f'Starting application with {worker_count} workers')

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.app