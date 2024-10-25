import jsonschema

from resonite_communities.models.community import Community
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.utils.logger import get_logger
from resonite_communities.models.base import BaseModel

class Signal:
    scheduler_type = None
    model = BaseModel

    def __init__(self, config, scheduler):
        self.name = self.__class__.__name__
        self.logger = get_logger(self.name)
        self.config = config
        self.scheduler = scheduler
        self.communities = []

        self._validate_scheduler_type()

        self._validate_jschema()

        self.valid_config = self._validate_signals_config()
        if self.valid_config:
            self.logger.info(f'Initialised events collector')

        self.update_communities()

    def _validate_scheduler_type(self):
        if not self.scheduler_type:
            raise ValueError(f"The collector {self.name} must have a declared scheduler type!")
        if self.scheduler_type not in SignalSchedulerType:
            raise ValueError(
                f"\n\nThe collector {self.name} have a non declared scheduler type: {self.scheduler_type}!"
                f"\nValid types are: {SignalSchedulerType.valid_types()}"
            )

    def _validate_jschema(self):
        if not self.jschema:
            raise ValueError(f"The collector {self.name} must have a declared json schema for its configuration!")

    def _validate_signals_config(self):
        """Validate signals configuration."""
        signals_config = getattr(self.config.SIGNALS, self.name, [])
        if not signals_config:
            self.logger.warning(f"Ignoring {self.name} events collector for now. No configuration found.")
            return False
        for signal_config in signals_config:
            try:
                jsonschema.validate(instance=signal_config, schema=self.jschema)
            except jsonschema.exceptions.ValidationError as exc:
                self.logger.warning(f"Ignoring events collector for now. Invalid schema: {exc.message}")
                return False
        return True

    def update_communities(self):
        self.communities = []
        for community in getattr(self.config.SIGNALS, self.name, []):
            community = Community(
                name=community['name'],
                monitored=False,
                external_id=str(community['external_id']),
                platform=self.name,
                tags=community['tags'],
                config=community.get('config', {})
            )
            Community.upsert(
                _filter_field='external_id',
                _filter_value=community.external_id,
                **community.dict()
            )
            self.communities.append(community)

    def add(self, **data):
        return self.model.add(**data)

    def get(self, **filters):
        return self.model.get(**filters)

    def update(self, _filter_field, _filter_value, **data):
        return self.model.update(_filter_field, _filter_value, **data)

    def upsert(self, _filter_field, _filter_value, **data):
        return self.model.upsert(_filter_field, _filter_value, **data)

    def delete(self, **filter):
        return self.model.delete(**filter)