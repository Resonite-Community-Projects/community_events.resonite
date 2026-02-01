from dateutil.parser import parse
import requests
import traceback

from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import EventStatus
from resonite_communities.signals.collectors.event import EventsCollector
from resonite_communities.signals import SignalSchedulerType


class CommunityEventsCollector(EventsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER
    platform = CommunityPlatform.JSON_COMMUNITY_EVENT

    def __init__(self, config, services, scheduler):
        super().__init__(config, services, scheduler)

    async def update_communities(self):
        self.communities = []
        for community in await Community.find(
            platform__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON],
            platform_on_remote__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON]
        ):
            await Community.update(
                filters=(
                    (Community.external_id == community.external_id) &
                    (Community.platform == community.platform) &
                    (Community.platform_on_remote == community.platform_on_remote)
                ),
                monitored=True,
            )
            self.communities.append(community)

    async def collect(self):
        await super().collect()
        self.logger.info(f'Starting collecting signals')
        await self.update_communities()
        for community in self.communities:
            try:
                self.logger.info(f'Collecting signals for {community.name}')
                if not community.config.get('community_configurator'):
                    self.logger.error(f"Invalid config for community '{community.name}': {community.config}")
                    continue
                community_configurator = (await Community.find(id=community.config.community_configurator))[0]

                response = requests.get(f"{community_configurator.config.events_url}/v2/events")

                if response.status_code != 200:
                    raise ValueError(f"{response.status_code} from server: {response.text}")

                for event in response.json():
                    if not event['community_name'] == community.name:
                        continue
                    await self.model.upsert(
                        _filter_field='external_id',
                        _filter_value=event['id'],
                        name=event['name'],
                        description=event['description'],
                        session_image=event['session_image'],
                        location=event['location_str'],
                        location_web_session_url=event['location_web_session_url'],
                        location_session_url=event['location_session_url'],
                        start_time=parse(event['start_time']),
                        end_time=parse(event['end_time']) if event['end_time'] else None,
                        community_id=community.id,
                        tags=event['tags'],
                        external_id=event['id'],
                        scheduler_type=self.scheduler_type.name,
                        status=event['status'],
                        created_at_external=None,
                        is_private='private' in event['tags'],
                        is_resonite='resonite' in event['tags'],
                        is_vrchat='vrchat' in event['tags'],
                    )
            except Exception as e:
                self.logger.error(f"Error processing community {community.name}: {str(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        self.logger.info(f'Finished collecting signals')
