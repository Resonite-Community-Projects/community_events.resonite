import jsonschema

from resonite_communities.signals import SignalSchedulerType

from resonite_communities.utils.logger import get_logger

class Collector:
    scheduler_type = None
    jschema = None

    def __init__(self, config, scheduler):
        self.name = self.__class__.__name__
        self.config = config
        self.scheduler = scheduler

        self.logger = get_logger(self.name)
        self._validate_jschema()
        self._validate_scheduler_type()

        self.valid_config = self._validate_signals_config()
        if self.valid_config:
            self.logger.info(f'Initialised events collector')

    def _validate_jschema(self):
        if not self.jschema:
            raise ValueError(f"The collector {self.name} must have a declared json schema for its configuration!")

    def _validate_scheduler_type(self):
        if not self.scheduler_type:
            raise ValueError(f"The collector {self.name} must have a declared scheduler type!")

        if self.scheduler_type not in SignalSchedulerType:
            raise ValueError(
                f"\n\nThe collector {self.name} have a non declared scheduler type: {self.scheduler_type}!"
                f"\nValid types are: {SignalSchedulerType.valid_types()}"
            )
# SignalSchedulerType
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