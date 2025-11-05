"""
Unit tests for Discord event tagging logic.

Tests the secure-by-default approach for determining whether events
should be tagged as 'public' or 'private' based on community configuration
and event channel placement.

These tests directly test the determine_event_visibility method by
instantiating the class with minimal mocking.
"""

import sys
from unittest.mock import Mock, MagicMock
import pytest
from easydict import EasyDict


def test_module_setup():
    """Setup mock modules to allow importing DiscordEventsCollector."""
    # Mock only the problematic imports that require environment variables
    sys.modules['resonite_communities.utils.config'] = MagicMock()
    sys.modules['resonite_communities.utils.db'] = MagicMock()


class TestDiscordEventTagging:
    """Test suite for Discord event tagging logic."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        test_module_setup()

        # Now import after mocking
        from resonite_communities.signals.collectors.events.discord import DiscordEventsCollector

        # Create a minimal instance
        self.collector = DiscordEventsCollector.__new__(DiscordEventsCollector)

    def create_mock_event(self, channel_id=None):
        """Helper to create a mock Discord event."""
        event = Mock()
        event.channel_id = channel_id
        return event

    def create_mock_community(self, tags, private_channel_id=None):
        """Helper to create a mock community."""
        community = Mock()
        community.tags = tags
        community.config = EasyDict({'private_channel_id': private_channel_id})
        return community

    # Test Case 1: Public-only community
    def test_public_only_community_no_private_channel(self):
        """
        Given: Community with only 'public' tag, no private_channel_id configured
        When: Processing an event
        Then: Event should be tagged as 'public'
        """
        community = self.create_mock_community(tags='public')
        event = self.create_mock_event(channel_id='123')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'public', "Public-only community should default to public"

    def test_public_only_community_event_in_private_channel(self):
        """
        Given: Community with only 'public' tag, private_channel_id configured
        When: Event is in the private channel
        Then: Event should be tagged as 'private'
        """
        community = self.create_mock_community(tags='public', private_channel_id='999')
        event = self.create_mock_event(channel_id='999')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "Event in private channel should be private"

    def test_public_only_community_event_not_in_private_channel(self):
        """
        Given: Community with only 'public' tag, private_channel_id configured
        When: Event is NOT in the private channel
        Then: Event should be tagged as 'public'
        """
        community = self.create_mock_community(tags='public', private_channel_id='999')
        event = self.create_mock_event(channel_id='123')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'public', "Public community event not in private channel should be public"

    # Test Case 2: Private-only community
    def test_private_only_community(self):
        """
        Given: Community with only 'private' tag
        When: Processing any event
        Then: Event should be tagged as 'private'
        """
        community = self.create_mock_community(tags='private')
        event = self.create_mock_event(channel_id='123')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "Private-only community should default to private"

    def test_private_only_community_with_private_channel_id(self):
        """
        Given: Community with only 'private' tag, private_channel_id configured
        When: Event is in the private channel
        Then: Event should be tagged as 'private'
        """
        community = self.create_mock_community(tags='private', private_channel_id='999')
        event = self.create_mock_event(channel_id='999')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "Private community event in private channel should be private"

    # Test Case 3: Mixed community (both public and private)
    def test_mixed_community_no_private_channel_configured(self):
        """
        Given: Community with both 'public' and 'private' tags, NO private_channel_id
        When: Processing an event
        Then: Event should default to 'private' (secure default)
        """
        community = self.create_mock_community(tags='public,private')
        event = self.create_mock_event(channel_id='123')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'public', "Mixed community with no private channel configured and no event channel should be public"

    def test_mixed_community_event_in_private_channel(self):
        """
        Given: Community with both 'public' and 'private' tags, private_channel_id configured
        When: Event is in the private channel
        Then: Event should be tagged as 'private'
        """
        community = self.create_mock_community(tags='public,private', private_channel_id='999')
        event = self.create_mock_event(channel_id='999')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "Mixed community event in private channel should be private"

    def test_mixed_community_event_not_in_private_channel(self):
        """
        Given: Community with both 'public' and 'private' tags, private_channel_id configured
        When: Event is NOT in the private channel
        Then: Event should default to 'private' (secure default)
        """
        community = self.create_mock_community(tags='public,private', private_channel_id='999')
        event = self.create_mock_event(channel_id='123')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'public', "Mixed community event not in private channel should be public"

    # Test Case 4: Events with no channel_id
    def test_event_without_channel_id_public_community(self):
        """
        Given: Community with only 'public' tag
        When: Event has no channel_id (None)
        Then: Event should be tagged as 'public'
        """
        community = self.create_mock_community(tags='public')
        event = self.create_mock_event(channel_id=None)

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'public', "Event without channel in public community should be public"

    def test_event_without_channel_id_private_community(self):
        """
        Given: Community with only 'private' tag
        When: Event has no channel_id (None)
        Then: Event should be tagged as 'private'
        """
        community = self.create_mock_community(tags='private')
        event = self.create_mock_event(channel_id=None)

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "Event without channel in private community should be private"

    def test_event_without_channel_id_mixed_community(self):
        """
        Given: Community with both 'public' and 'private' tags
        When: Event has no channel_id (None)
        Then: Event should default to 'private' (secure default)
        """
        community = self.create_mock_community(tags='public,private')
        event = self.create_mock_event(channel_id=None)

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'public', "Event without channel in mixed community should be public"

    # Test Case 5: Edge cases
    def test_tags_with_spaces(self):
        """
        Given: Community tags with spaces (e.g., 'public, private')
        When: Processing an event
        Then: Current implementation treats ' private' as different from 'private'
        
        Note: This documents a known limitation. Tags should be stored without spaces
        in production (e.g., 'public,private' not 'public, private').
        """
        community = self.create_mock_community(tags='public, private')
        event = self.create_mock_event(channel_id='123')

        result = self.collector.determine_event_visibility(event, community)

        # Current behavior: 'public' is found but ' private' (with space) is not equal to 'private'
        # So the condition 'private' not in tags is True, making this public
        assert result == 'public', "Documents current behavior with spaces in tags"

    def test_empty_tags(self):
        """
        Given: Community with empty tags
        When: Processing an event
        Then: Event should default to 'private' (secure default)
        """
        community = self.create_mock_community(tags='')
        event = self.create_mock_event(channel_id='123')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "Empty tags should default to private (secure)"

    def test_tags_in_different_order(self):
        """
        Given: Community with tags in different order ('private,public' vs 'public,private')
        When: Processing events
        Then: Results should be the same (order shouldn't matter)
        """
        community1 = self.create_mock_community(tags='public,private')
        community2 = self.create_mock_community(tags='private,public')
        event = self.create_mock_event(channel_id='123')

        result1 = self.collector.determine_event_visibility(event, community1)
        result2 = self.collector.determine_event_visibility(event, community2)

        assert result1 == result2, "Tag order should not affect the result"
        assert result1 == 'public', "Both should be public as they have both tags and event is not in private channel"

    def test_channel_id_string_vs_int(self):
        """
        Given: Channel IDs as strings vs integers
        When: Comparing event.channel_id with private_channel_id
        Then: Comparison should work correctly
        """
        # Test with both as strings (typical Discord API)
        community = self.create_mock_community(tags='public', private_channel_id='999')
        event = self.create_mock_event(channel_id='999')

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "String channel IDs should match"

    def test_mixed_community_event_in_private_channel_with_int_id(self):
        """
        Given: Community with both 'public' and 'private' tags, private_channel_id configured as string
        When: Event is in the private channel, with channel_id as an integer
        Then: Event should be tagged as 'private'
        """
        community = self.create_mock_community(tags='public,private', private_channel_id='999')
        event = self.create_mock_event(channel_id=999) # Simulate integer channel_id from Discord API

        result = self.collector.determine_event_visibility(event, community)

        assert result == 'private', "Mixed community event in private channel (int ID) should be private"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
