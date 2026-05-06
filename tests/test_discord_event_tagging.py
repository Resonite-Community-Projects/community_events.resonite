import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from easydict import EasyDict
from freezegun import freeze_time
from disnake import GuildScheduledEvent

sys.modules['resonite_communities.utils.config'] = MagicMock()
sys.modules['resonite_communities.utils.db'] = MagicMock()

from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.signals.collectors.events.discord import DiscordEventsCollector
from resonite_communities.models.signal import Event, EventStatus

class _DiscordState:
    def get_user(self, user_id):
        return None

def create_event(channel_id=None):
    return GuildScheduledEvent(state=_DiscordState(), data={
        'id': '1',
        'guild_id': '1',
        'channel_id': str(channel_id) if channel_id is not None else None,
        'creator_id': None,
        'name': 'Test Event',
        'scheduled_start_time': '2025-01-01T00:00:00+00:00',
        'scheduled_end_time': None,
        'privacy_level': 2,
        'status': 1,
        'entity_type': 2,
        'entity_id': None,
        'entity_metadata': None,
    })

def create_community(tags, private_channel_id=None):
    return Community(
        created_at=datetime.now(timezone.utc),
        external_id='test',
        platform=CommunityPlatform.DISCORD,
        name='Test Community',
        monitored=False,
        tags=tags,
        config=EasyDict({'private_channel_id': private_channel_id})
    )
class TestDiscordEventTagging:

    # Test Case 1: Public-only community
    def test_public_only_community_no_private_channel(self):
        community = create_community(tags='public')
        event = create_event(channel_id='123')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'public'

    def test_public_only_community_event_in_private_channel(self):
        community = create_community(tags='public', private_channel_id='999')
        event = create_event(channel_id='999')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    def test_public_only_community_event_not_in_private_channel(self):
        community = create_community(tags='public', private_channel_id='999')
        event = create_event(channel_id='123')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'public'

    # Test Case 2: Private-only community
    def test_private_only_community(self):
        community = create_community(tags='private')
        event = create_event(channel_id='123')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    def test_private_only_community_with_private_channel_id(self):
        community = create_community(tags='private', private_channel_id='999')
        event = create_event(channel_id='999')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    # Test Case 3: Mixed community (both public and private)
    def test_mixed_community_no_private_channel_configured(self):
        community = create_community(tags='public,private')
        event = create_event(channel_id='123')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'public'

    def test_mixed_community_event_in_private_channel(self):
        community = create_community(tags='public,private', private_channel_id='999')
        event = create_event(channel_id='999')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    def test_mixed_community_event_not_in_private_channel(self):
        community = create_community(tags='public,private', private_channel_id='999')
        event = create_event(channel_id='123')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'public'

    # Test Case 4: Events with no channel_id
    def test_event_without_channel_id_public_community(self):
        community = create_community(tags='public')
        event = create_event(channel_id=None)
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'public'

    def test_event_without_channel_id_private_community(self):
        community = create_community(tags='private')
        event = create_event(channel_id=None)
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    def test_event_without_channel_id_mixed_community(self):
        community = create_community(tags='public,private')
        event = create_event(channel_id=None)
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'public'

    # Test Case 5: Edge cases
    def test_tags_with_spaces_public(self):
        community = create_community(tags='public, private')
        event = create_event(channel_id='123')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'public'

    def test_tags_with_spaces_private(self):
        community = create_community(tags='public, private', private_channel_id='999')
        event = create_event(channel_id='999')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    def test_empty_tags(self):
        community = create_community(tags='')
        event = create_event(channel_id='123')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    def test_tags_in_different_order(self):
        community1 = create_community(tags='public,private')
        community2 = create_community(tags='private,public')
        event = create_event(channel_id='123')
        event_visibility_1 = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community1)
        event_visibility_2 = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community2)
        assert event_visibility_1 == event_visibility_2, "Tag order should not affect the result"
        assert event_visibility_2 == 'public', "Both should be public as they have both tags and event is not in private channel"

    def test_channel_id_string_vs_int(self):
        community = create_community(tags='public', private_channel_id=999)
        event = create_event(channel_id='999')
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

    def test_private_channel_id_string_vs_int(self):
        community = create_community(tags='public', private_channel_id='999')
        event = create_event(channel_id=999)
        event_visibility = DiscordEventsCollector(config=None, services=None, scheduler=None).determine_event_visibility(event, community)
        assert event_visibility == 'private'

@freeze_time("2023-10-6T18:00:00+00:00")
class TestDiscordIsCancel:

    def test_event_with_end_time_in_the_past(self):
        local_event = Event(
            created_at=datetime(2023, 10, 6, 18, 0, 0, tzinfo=timezone.utc),
            external_id='resonite',
            name='Fluffy opening!',
            start_time=datetime(2023, 10, 6, 19, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 10, 6, 18, 0, 0, tzinfo=timezone.utc),
            community_id=uuid4(),
            scheduler_type='DISCORD',
            status=EventStatus.READY,
        )
        is_cancel = DiscordEventsCollector.is_cancel(None, local_event)
        assert is_cancel == None

    def test_event_with_end_time_in_the_future(self):
        local_event = Event(
            created_at=datetime(2023, 10, 6, 18, 0, 0, tzinfo=timezone.utc),
            external_id='resonite',
            name='Fluffy opening!',
            start_time=datetime(2023, 10, 6, 19, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 10, 6, 20, 0, 0, tzinfo=timezone.utc),
            community_id=uuid4(),
            scheduler_type='DISCORD',
            status=EventStatus.READY,
        )
        is_cancel = DiscordEventsCollector.is_cancel(None, local_event)
        assert is_cancel == None

    def test_event_without_end_time_start_time_in_the_past(self):
        local_event = Event(
            created_at=datetime(2023, 10, 6, 18, 0, 0, tzinfo=timezone.utc),
            external_id='resonite',
            name='Fluffy opening!',
            start_time=datetime(2023, 10, 6, 17, 0, 0, tzinfo=timezone.utc),
            community_id=uuid4(),
            scheduler_type='DISCORD',
            status=EventStatus.READY,
        )
        is_cancel = DiscordEventsCollector.is_cancel(None, local_event)
        assert is_cancel == True

    def test_event_without_end_time_start_time_in_the_future(self):
        local_event = Event(
            created_at=datetime(2023, 10, 6, 18, 0, 0, tzinfo=timezone.utc),
            external_id='resonite',
            name='Fluffy opening!',
            start_time=datetime(2023, 10, 6, 20, 0, 0, tzinfo=timezone.utc),
            community_id=uuid4(),
            scheduler_type='DISCORD',
            status=EventStatus.READY,
        )
        is_cancel = DiscordEventsCollector.is_cancel(None, local_event)
        assert is_cancel == None
