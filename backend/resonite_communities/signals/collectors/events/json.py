from dateutil.parser import parse
import requests

from resonite_communities.models import EventStatus
from resonite_communities.signals.collectors.event import EventsCollector
from resonite_communities.signals import SignalSchedulerType


class JSONEventsCollector(EventsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER
    jschema = {
        "$schema":"http://json-schema.org/draft-04/schema#",
        "title":"JsonEventsConfig",
        "description":"Config for JSON collector",
        "type":"object",
        "properties":{
            "community_external_id": {
                "description": "The id of the community",
                "type": "string"
            },
            "community_name": {
                "description": "The name of the community",
                "type": "string"
            },
            "community_description": {
                "description": "The description of the community",
                "type": "string"
            },
            "events_url":{
                "description":"The URL to get events from",
                "type": "string"
            },
            "tags":{
                "description":"A list of tags",
                "type": "array"
            }
        },
        "required":[
            "community_name",
            "events_url",
        ]
    }

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

        self.communities = []

    def update_config(self):
        for bot_config in getattr(self.config.SIGNALS, self.name, []):
            self.communities.append(bot_config)

    def collect(self):
        self.logger.info('Update events collector from external source')
        self.update_config()
        for community in self.communities:
            self.logger.info(f"Processing events for {community['community_name']} from {community['events_url']}")

            try:
                response = requests.get(community['events_url'])
            except:
                self.logger.error(f"Exception on request for {community['community_name']}")
                self.logger.error("Skipping")
                continue

            if response.status_code != 200:
                self.logger.error(f"Error {response.status_code} from {community['community_name']} server: {response.text}")
                self.logger.error("Skipping")
                continue

            for event in response.json():
                self.model.upsert(
                    _filter_field='external_id',
                    _filter_value=event['event_id'],
                    name=event['name'],
                    description=event['description'],
                    session_image=None,
                    location=event['location'],
                    location_web_session_url=self.get_location_web_session_url(event['description']),
                    location_session_url=event['session_url'],
                    start_time=parse(event['start_time']),
                    end_time=parse(event['end_time']),
                    community_url=community.community_url,
                    community_name=community.community_name,
                    community_external_id=community.community_external_id,
                    tags=",".join(community.tags),
                    external_id=event['event_id'],
                    scheduler_type=self.scheduler_type.name,
                    status=EventStatus.READY,
                    created_at_external=None,
                )

