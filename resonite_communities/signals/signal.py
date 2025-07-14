from copy import deepcopy

from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.utils.logger import get_logger
from resonite_communities.models.base import BaseModel

class Signal:
    scheduler_type = None
    platform = None
    model = BaseModel

    def __init__(self, config, services, scheduler):
        self.name = self.__class__.__name__
        self.logger = get_logger(self.name)
        self.config = config
        self.services = services
        self.scheduler = scheduler
        self.communities = []

        self._validate_scheduler_type()

        self._validate_platform()

        self.logger.info(f'Initialised {self.name} collector')

    def _validate_scheduler_type(self):
        if not self.scheduler_type:
            raise ValueError(f"The collector {self.name} must have a declared scheduler type!")
        if self.scheduler_type not in SignalSchedulerType:
            raise ValueError(
                f"\n\nThe collector {self.name} have a non declared scheduler type: {self.scheduler_type}!"
                f"\nValid types are: {SignalSchedulerType.valid_values()}"
            )

    def _validate_platform(self):
        if not self.platform:
            raise ValueError(f"The collector {self.name} must have a declared platform!")
        if self.platform not in CommunityPlatform:
            raise ValueError(
                f"\n\nThe collector {self.name} have a non declared platform: {self.platform}!"
                f"\nValid platforms are: {CommunityPlatform.valid_values()}"
            )

    def update_communities(self):
        raise ValueError("Not implemented")

    def add(self, **data):
        return self.model.add(**data)

    def get(self, **filters):
        return self.model.get(**filters)

    def update(self, filters, **data):
        return self.model.update(filters=filters, **data)

    def upsert(self, _filter_field, _filter_value, **data):
        return self.model.upsert(_filter_field, _filter_value, **data)

    def delete(self, **filter):
        return self.model.delete(**filter)