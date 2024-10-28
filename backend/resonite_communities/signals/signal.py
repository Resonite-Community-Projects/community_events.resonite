import jsonschema

from resonite_communities.models.community import Community
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.utils.logger import get_logger
from resonite_communities.models.base import BaseModel

def gen_schema(
    title: str,
    description: str,
    property_external_id: str = "The id of the community",
    property_external_id_type: str = "integer",
    property_name: str = "The name of the community.",
    property_name_type: str = "string",
    property_description: str = "The description of the community.",
    property_description_type: str = "string",
    property_url: str = "The link related to the community.",
    property_url_type: str = "string",
    property_tags: str = "The tags related to the community.",
    property_tags_type: str = "array",
    property_config: str = "The config related to the community",
    property_config_type: str = "object",
    properties_required: list = [
            "external_id",
            "name",
            "url",
            "tags",
    ],
):
    return {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "title": title,
            "description": description,
            "type": "object",
            "properties": {
                "external_id":{
                    "description": property_external_id,
                    "type": property_external_id_type,
                },
                "name": {
                    "description": property_name,
                    "type": property_name_type,
                },
                "description": {
                    "description": property_description,
                    "type": property_description_type,
                },
                "url": {
                    "description": property_url,
                    "type": property_url_type,
                },
                "tags": {
                    "description": property_tags,
                    "type": property_tags_type,
                },
                "config": {
                    "description": property_config,
                    "type": property_config_type,
                },
            },
            "required": properties_required,
        }

class Signal:
    scheduler_type = None
    jschema = None
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
            self.update_communities()
            self.logger.info(f'Initialised events collector')

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
                tags=community.get('tags', []),
                config=community.get('config', {})
            )
            Community.upsert(
                _filter_field=['external_id', 'platform'],
                _filter_value=[community.external_id, community.platform],
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