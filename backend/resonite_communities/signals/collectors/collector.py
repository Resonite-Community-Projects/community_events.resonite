import logging
import jsonschema

from flask.logging import default_handler

class Collector:
    signal_type = None
    jschema = None

    FORMATTER_STRING = '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S %z"

    def __init__(self, config, scheduler):
        self.name = self.__class__.__name__
        self.config = config
        self.scheduler = scheduler

        self.logger = self._initialize_logger()

        self._validate_jschema()
        self._validate_signal_type()

        self.valid_config = self._validate_signals_config()
        if self.valid_config:
            self.logger.info(f'Initialised events collector')

    def _initialize_logger(self):
        """Initialize and configure the logger."""
        formatter = logging.Formatter(
            self.FORMATTER_STRING,
            self.DATE_FORMAT,
        )
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        logger.addHandler(default_handler)
        logger.handlers[0].setFormatter(formatter)
        return logger

    def _validate_jschema(self):
        if not self.jschema:
            raise ValueError(f"The collector {self.name} must have a declared json schema for its configuration!")

    def _validate_signal_type(self):
        if not self.signal_type:
            raise ValueError(f"The collector {self.name} must have a declared signal type!")

    def _validate_signals_config(self):
        """Validate signals configuration."""
        signals_config = getattr(self.config.SIGNALS, self.name, [])
        if not signals_config:
            self.logger.warning(f"Ignoring events collector for now. No configuration found.")
            return False
        for signal_config in signals_config:
            try:
                jsonschema.validate(instance=signal_config, schema=self.jschema)
            except jsonschema.exceptions.ValidationError as exc:
                self.logger.warning(f"Ignoring events collector for now. Invalid schema: {exc.message}")
                return False
        return True

    def collect(self):
        self.logger.info('Update events collector')

    def init_scheduler(self):
        # You **must** call this method in your collector __init__ method
        self.logger.info('Events collector ready')
        self.scheduler.add_job(self.collect,'interval', minutes=self.config.discord_refresh_interval)
        self.collect()