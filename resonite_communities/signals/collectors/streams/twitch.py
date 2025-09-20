from dateutil.parser import parse
import traceback

from resonite_communities.models.community import CommunityPlatform, Community
from resonite_communities.models.signal import EventStatus
from resonite_communities.signals import SignalSchedulerType

from resonite_communities.signals.collectors.stream import StreamsCollector


class TwitchStreamsCollector(StreamsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER
    platform = CommunityPlatform.TWITCH
    broadcasters = []

    def __init__(self, config, services, scheduler):
        super().__init__(config, services, scheduler)
        if not self.services.twitch.ready:
            self.logger.warning('Not ready, no twitch community update')

    async def update_communities(self):
        self.communities = []
        self.broadcasters = []
        if not self.services.twitch.ready:
            return
        for streamer in await Community.find(platform__in=[CommunityPlatform.TWITCH]):
            broadcaster = dict()
            broadcaster['config'] = streamer
            try:
                broadcaster['twitch'] = self.services.twitch.get_broadcaster_info(streamer)
            except ValueError as exc:
                self.logger.error(exc)
                continue
            await Community.upsert(
                _filter_field=['external_id', 'platform'],
                _filter_value=[streamer.external_id, CommunityPlatform.TWITCH],
                name=streamer.name,
                platform=CommunityPlatform.TWITCH,
                monitored=streamer.monitored,
                external_id=streamer.external_id,
                members_count=broadcaster['twitch']['followers']['total'],
                logo=broadcaster['twitch']['profile_image_url'],
            )
            if not any(b.get('id') == broadcaster['twitch']['id'] for b in self.broadcasters):
                self.broadcasters.append(broadcaster)
            self.communities.append(streamer)

    async def collect(self):
        await super().collect()
        if not self.services.twitch.ready:
            return
        self.logger.info('Update streams collector')
        await self.update_communities()

        for broadcaster in self.broadcasters:
            try:
                broadcaster_streams = self.services.twitch.get_schedule(broadcaster['twitch'])
                for broadcaster_stream in broadcaster_streams:
                    await self.model.upsert(
                        _filter_field='external_id',
                        _filter_value=broadcaster_stream['id'],
                        name=broadcaster_stream['title'],
                        start_time=parse(broadcaster_stream['start_time']),
                        end_time=parse(broadcaster_stream['end_time']),
                        community_id=(await Community.find(external_id=broadcaster['config'].external_id))[0].id,
                        tags=",".join(broadcaster.get('config', {}).tags),
                        external_id=broadcaster_stream['id'],
                        scheduler_type=self.scheduler_type.name,
                        status=EventStatus.READY,
                    )
            except Exception as e:
                self.logger.error(f"Error processing community {broadcaster_stream['id']}: {str(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                continue
