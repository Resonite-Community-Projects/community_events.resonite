from dateutil.parser import parse

from resonite_communities.models.community import CommunityPlatform, Community
from resonite_communities.models.signal import EventStatus
from resonite_communities.signals import SignalSchedulerType

from resonite_communities.signals.collectors.stream import StreamsCollector
from resonite_communities.signals.signal import gen_schema


class TwitchStreamsCollector(StreamsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER
    platform = CommunityPlatform.TWITCH
    jschema = gen_schema(
        title="TwitchConfig",
        description="The Twitch configuration of a streamer.",
        property_external_id="The exact id of the Streamer, as in the url.",
        property_name="The general name of the streamer.",
        property_description="The description of the streamer.",
        property_url="The custom link to the stream channel, if anny.",
        property_tags="The tags about this Twitch streamer.",
        property_config="The special configuration of this streamer.",
        properties_required=[
            "external_id",
            "name",
        ]
    )
    broadcasters = []

    def update_communities(self):

        for streamer in self.communities:
            broadcaster = dict()
            broadcaster['config'] = streamer
            try:
                broadcaster['twitch'] = self.services.twitch.get_broadcaster_info(streamer)
            except ValueError as exc:
                self.logger.error(exc)
                continue
            Community.upsert(
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

    def collect(self):
        self.logger.info('Update streams collector')
        self.update_communities()

        for broadcaster in self.broadcasters:
            broadcaster_streams = self.services.twitch.get_schedule(broadcaster['twitch'])
            for broadcaster_stream in broadcaster_streams:
                self.model.upsert(
                    _filter_field='external_id',
                    _filter_value=broadcaster_stream['id'],
                    name=broadcaster_stream['title'],
                    start_time=parse(broadcaster_stream['start_time']),
                    end_time=parse(broadcaster_stream['end_time']),
                    community_id=Community.find(external_id=broadcaster['config'].external_id)[0].id,
                    tags=",".join(broadcaster['config'].tags),
                    external_id=broadcaster_stream['id'],
                    scheduler_type=self.scheduler_type.name,
                    status=EventStatus.READY,
                )

