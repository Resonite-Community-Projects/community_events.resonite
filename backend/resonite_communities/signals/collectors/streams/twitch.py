from resonite_communities.models.community import CommunityPlatform
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
        super().update_communities()

        for streamer in self.communities:
            broadcaster = self.config.clients.twitch.get_broadcaster_info(streamer)
            if not any(b.get('id') == broadcaster['id'] for b in self.broadcasters):
                self.broadcasters.append(broadcaster)

    def collect(self):
        self.logger.info(f'Update streams collector IN MODULE')
        self.update_communities()

        streams = []

        for broadcaster in self.broadcasters:
            broadcaster_streams = self.config.clients.twitch.get_schedule(broadcaster)
            for broadcaster_stream in broadcaster_streams:
                streams.append(broadcaster_stream)

        for stream in streams:
            # TODO: save in database instead of logging them
            self.logger.error(stream)
