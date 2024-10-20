from typing import Any, Optional

from resonite_communities.signals import SignalSchedulerType
from resonite_communities.utils.logger import get_logger
from resonite_communities.models import Signal as SignalModel

class Signal:
    scheduler_type = None
    model = SignalModel

    def __init__(self):
        self.name = self.__class__.__name__
        self.logger = get_logger(self.name)

        self._validate_scheduler_type()

    def _validate_scheduler_type(self):
        if not self.scheduler_type:
            raise ValueError(f"The collector {self.name} must have a declared scheduler type!")
        if self.scheduler_type not in SignalSchedulerType:
            raise ValueError(
                f"\n\nThe collector {self.name} have a non declared scheduler type: {self.scheduler_type}!"
                f"\nValid types are: {SignalSchedulerType.valid_types()}"
            )

    def add(self, **data):
        return self.model.add(**data)

    def get(self, **filters):
        return self.model.get(**filters)

    def update(self, _filter_field, _filter_value, **data):
        return self.model.update(_filter_field, _filter_value, **data)

    def delete(self, **filter):
        return self.model.delete(**filter)