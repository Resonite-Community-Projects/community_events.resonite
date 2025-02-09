from dateutil.parser import parse
import requests

from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import EventStatus
from resonite_communities.signals.collectors.event import EventsCollector
from resonite_communities.signals import SignalSchedulerType
from resonite_communities.signals.signal import gen_schema


class JSONEventsCollector(EventsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER
    platform = CommunityPlatform.JSON
    jschema = gen_schema(
        title = "JSONConfig",
        description = "The configuration of an external source in JSON.",
        property_external_id_type = "string",
    )

    def __init__(self, config, services, scheduler):
        super().__init__(config, services, scheduler)

    def update_communities(self):
        for community in self.communities:
            Community.update(
                _filter_field=['external_id', 'platform'],
                _filter_value=[community.external_id, CommunityPlatform.JSON],
                monitored=True,
            )

    def collect(self):
        self.logger.info('Update events collector from external source')
        self.update_communities()
        for community in self.communities:
            self.logger.info(f"Processing events for {community.name} from {community.config.events_url}")

            try:
                response = requests.get(community.config.events_url)
            except Exception as error:
                self.logger.error(f"Exception on request for {community.name}")
                self.logger.error(error)
                self.logger.error("Skipping")
                continue

            if response.status_code != 200:
                self.logger.error(f"Error {response.status_code} from {community.name} server: {response.text}")
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
                    community_id=Community.find(external_id=community.external_id)[0].id,
                    tags=",".join(community.tags),
                    external_id=event['event_id'],
                    scheduler_type=self.scheduler_type.name,
                    status=EventStatus.READY,
                    created_at_external=None,
                )

