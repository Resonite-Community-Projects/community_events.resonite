from dateutil.parser import parse
import requests
import traceback

from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import EventStatus
from resonite_communities.signals.collectors.event import EventsCollector
from resonite_communities.signals import SignalSchedulerType


class JSONEventsCollector(EventsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER
    platform = CommunityPlatform.JSON

    def __init__(self, config, services, scheduler):
        super().__init__(config, services, scheduler)

    async def update_communities(self):
        self.communities = []
        for community in await Community.find(platform__in=[CommunityPlatform.JSON]):
            await Community.update(
                filters=(
                    (Community.external_id == community.external_id) &
                    (Community.platform == CommunityPlatform.JSON)
                ),
                monitored=True,
            )
            self.communities.append(community)

    async def collect(self):
        await super().collect()
        self.logger.info('Update events collector from external source')
        await self.update_communities()
        for community in self.communities:
            try:
                self.logger.info(f"Processing events for {community.name} from {community.config.events_url}")

                response = requests.get(community.config.events_url)

                if response.status_code != 200:
                    raise ValueError(f"{response.status_code} from server: {response.text}")

                for event in response.json():
                    await self.model.upsert(
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
                        community_id=(await Community.find(external_id=community.external_id))[0].id,
                        tags=community.tags,
                        external_id=event['event_id'],
                        scheduler_type=self.scheduler_type.name,
                        status=EventStatus.READY,
                        created_at_external=None,
                    )
            except Exception as e:
                self.logger.error(f"Error processing community {community.name}: {str(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                continue
