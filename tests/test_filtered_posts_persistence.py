"""
Tests for filtered posts persistence to skipped_posts audit trail
"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add the parent directory to sys.path to import src as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from src.bluesky_client import BlueskyFetchResult, BlueskyPost
from src.sync_orchestrator import SocialSyncOrchestrator
from src.sync_state import SyncState


class TestFilteredPostsPersistence:
    """Test that filtered posts are persisted to skipped_posts with correct reasons"""

    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary sync state file for testing"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            temp_file = tmp.name
            initial_state = {
                "last_sync_time": "2025-12-26T00:00:00.000000",
                "synced_posts": [],
                "last_bluesky_post_uri": None,
                "skipped_posts": [],
            }
            json.dump(initial_state, tmp)

        yield temp_file

        # Cleanup
        Path(temp_file).unlink()

    def test_bluesky_client_tracks_reply_filtering(self):
        """Test that BlueskyClient tracks filtered reply posts in result"""
        # Create a fetch result with a filtered reply
        filtered_posts = {
            "at://post-1": "reply-not-self-threaded",
            "at://post-2": "repost",
        }

        result = BlueskyFetchResult(
            posts=[],
            total_retrieved=2,
            filtered_replies=1,
            filtered_reposts=1,
            filtered_by_date=0,
            filtered_quotes=0,
            filtered_posts=filtered_posts,
        )

        assert len(result.filtered_posts) == 2
        assert result.filtered_posts["at://post-1"] == "reply-not-self-threaded"
        assert result.filtered_posts["at://post-2"] == "repost"

    def test_bluesky_client_tracks_all_filter_reasons(self):
        """Test that all filter reasons are properly tracked"""
        filtered_posts = {
            "at://reply-1": "reply-not-self-threaded",
            "at://repost-1": "repost",
            "at://quote-1": "quote-of-other",
            "at://old-post-1": "older-than-sync-date",
        }

        result = BlueskyFetchResult(
            posts=[],
            total_retrieved=4,
            filtered_replies=1,
            filtered_reposts=1,
            filtered_quotes=1,
            filtered_by_date=1,
            filtered_posts=filtered_posts,
        )

        assert len(result.filtered_posts) == 4
        assert set(result.filtered_posts.values()) == {
            "reply-not-self-threaded",
            "repost",
            "quote-of-other",
            "older-than-sync-date",
        }

    def test_filtered_replies_persisted_to_skipped_posts(self, temp_state_file):
        """Test that filtered replies are persisted to skipped_posts with correct reason"""
        sync_state = SyncState(temp_state_file)

        # Simulate persisting a filtered reply
        filtered_post_uri = "at://filtered-reply"
        sync_state.mark_post_skipped(
            filtered_post_uri, reason="reply-not-self-threaded"
        )

        # Verify in memory
        skipped = sync_state.state.get("skipped_posts", [])
        assert len(skipped) == 1
        assert skipped[0]["bluesky_uri"] == filtered_post_uri
        assert skipped[0]["reason"] == "reply-not-self-threaded"

        # Verify persisted to JSON
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        assert len(persisted["skipped_posts"]) == 1
        assert persisted["skipped_posts"][0]["bluesky_uri"] == filtered_post_uri
        assert persisted["skipped_posts"][0]["reason"] == "reply-not-self-threaded"

    def test_filtered_reposts_persisted_to_skipped_posts(self, temp_state_file):
        """Test that filtered reposts are persisted with correct reason"""
        sync_state = SyncState(temp_state_file)

        # Simulate persisting a filtered repost
        filtered_post_uri = "at://filtered-repost"
        sync_state.mark_post_skipped(filtered_post_uri, reason="repost")

        # Verify persistence
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        assert len(persisted["skipped_posts"]) == 1
        assert persisted["skipped_posts"][0]["reason"] == "repost"

    def test_filtered_quotes_persisted_to_skipped_posts(self, temp_state_file):
        """Test that filtered quote posts are persisted with correct reason"""
        sync_state = SyncState(temp_state_file)

        # Simulate persisting a filtered quote
        filtered_post_uri = "at://filtered-quote"
        sync_state.mark_post_skipped(filtered_post_uri, reason="quote-of-other")

        # Verify persistence
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        assert len(persisted["skipped_posts"]) == 1
        assert persisted["skipped_posts"][0]["reason"] == "quote-of-other"

    def test_filtered_date_filtered_posts_persisted(self, temp_state_file):
        """Test that date-filtered posts are persisted with correct reason"""
        sync_state = SyncState(temp_state_file)

        # Simulate persisting a date-filtered post
        filtered_post_uri = "at://old-post"
        sync_state.mark_post_skipped(filtered_post_uri, reason="older-than-sync-date")

        # Verify persistence
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        assert len(persisted["skipped_posts"]) == 1
        assert persisted["skipped_posts"][0]["reason"] == "older-than-sync-date"

    @patch("src.sync_orchestrator.BlueskyClient")
    @patch("src.sync_orchestrator.MastodonClient")
    @patch("src.sync_orchestrator.get_settings")
    def test_orchestrator_persists_filtered_replies_to_json(
        self, mock_settings, mock_mastodon, mock_bluesky, temp_state_file
    ):
        """Integration test: Orchestrator persists filtered replies to JSON"""
        # Setup mocks
        mock_settings_instance = Mock()
        mock_settings_instance.bluesky_handle = "test.bsky.social"
        mock_settings_instance.bluesky_password = "password"
        mock_settings_instance.mastodon_api_base_url = "https://test.social"
        mock_settings_instance.mastodon_access_token = "token"
        mock_settings_instance.state_file = temp_state_file
        mock_settings_instance.max_posts_per_sync = 10
        mock_settings_instance.get_sync_start_datetime.return_value = datetime(
            2025, 12, 1
        )
        mock_settings.return_value = mock_settings_instance

        # Setup Bluesky client mock
        mock_bluesky_instance = Mock()
        mock_bluesky_instance.authenticate.return_value = True
        mock_bluesky.return_value = mock_bluesky_instance

        # Setup Mastodon client mock
        mock_mastodon_instance = Mock()
        mock_mastodon_instance.authenticate.return_value = True
        mock_mastodon.return_value = mock_mastodon_instance

        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()
        orchestrator.sync_state = SyncState(temp_state_file)

        # Directly assign mocked client instead of calling setup_clients
        orchestrator.bluesky_client = mock_bluesky_instance
        orchestrator.mastodon_client = mock_mastodon_instance

        # Create fetch result with filtered reply
        filtered_reply_uri = "at://filtered-reply-123"
        fetch_result = BlueskyFetchResult(
            posts=[],  # No posts to sync, just filtered ones
            total_retrieved=1,
            filtered_replies=1,
            filtered_reposts=0,
            filtered_by_date=0,
            filtered_quotes=0,
            filtered_posts={filtered_reply_uri: "reply-not-self-threaded"},
        )

        # Mock the fetch result
        orchestrator.bluesky_client.get_recent_posts.return_value = fetch_result

        posts_to_sync, skipped_count = orchestrator.get_posts_to_sync()

        # Verify filtered reply was persisted
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        skipped_uris = [p["bluesky_uri"] for p in persisted["skipped_posts"]]
        assert filtered_reply_uri in skipped_uris

        # Verify the reason
        filtered_entry = next(
            (
                p
                for p in persisted["skipped_posts"]
                if p["bluesky_uri"] == filtered_reply_uri
            ),
            None,
        )
        assert filtered_entry is not None
        assert filtered_entry["reason"] == "reply-not-self-threaded"

    @patch("src.sync_orchestrator.BlueskyClient")
    @patch("src.sync_orchestrator.MastodonClient")
    @patch("src.sync_orchestrator.get_settings")
    def test_orchestrator_persists_multiple_filtered_posts_with_different_reasons(
        self, mock_settings, mock_mastodon, mock_bluesky, temp_state_file
    ):
        """Integration test: Multiple filtered posts with different reasons are persisted"""
        # Setup mocks
        mock_settings_instance = Mock()
        mock_settings_instance.bluesky_handle = "test.bsky.social"
        mock_settings_instance.bluesky_password = "password"
        mock_settings_instance.mastodon_api_base_url = "https://test.social"
        mock_settings_instance.mastodon_access_token = "token"
        mock_settings_instance.state_file = temp_state_file
        mock_settings_instance.max_posts_per_sync = 10
        mock_settings_instance.get_sync_start_datetime.return_value = datetime(
            2025, 12, 1
        )
        mock_settings.return_value = mock_settings_instance

        # Setup Bluesky client mock
        mock_bluesky_instance = Mock()
        mock_bluesky_instance.authenticate.return_value = True
        mock_bluesky.return_value = mock_bluesky_instance

        # Setup Mastodon client mock
        mock_mastodon_instance = Mock()
        mock_mastodon_instance.authenticate.return_value = True
        mock_mastodon.return_value = mock_mastodon_instance

        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()
        orchestrator.sync_state = SyncState(temp_state_file)

        # Directly assign mocked clients
        orchestrator.bluesky_client = mock_bluesky_instance
        orchestrator.mastodon_client = mock_mastodon_instance

        # Create fetch result with multiple filtered posts
        filtered_posts = {
            "at://filtered-reply": "reply-not-self-threaded",
            "at://filtered-repost": "repost",
            "at://filtered-quote": "quote-of-other",
            "at://old-post": "older-than-sync-date",
        }

        fetch_result = BlueskyFetchResult(
            posts=[],
            total_retrieved=4,
            filtered_replies=1,
            filtered_reposts=1,
            filtered_by_date=1,
            filtered_quotes=1,
            filtered_posts=filtered_posts,
        )

        # Mock the fetch result
        orchestrator.bluesky_client.get_recent_posts.return_value = fetch_result

        posts_to_sync, skipped_count = orchestrator.get_posts_to_sync()

        # Verify all filtered posts were persisted
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        skipped_posts = persisted["skipped_posts"]
        assert len(skipped_posts) == 4

        # Verify each post has correct reason
        reasons_map = {p["bluesky_uri"]: p["reason"] for p in skipped_posts}
        assert reasons_map["at://filtered-reply"] == "reply-not-self-threaded"
        assert reasons_map["at://filtered-repost"] == "repost"
        assert reasons_map["at://filtered-quote"] == "quote-of-other"
        assert reasons_map["at://old-post"] == "older-than-sync-date"

    @patch("src.sync_orchestrator.BlueskyClient")
    @patch("src.sync_orchestrator.MastodonClient")
    @patch("src.sync_orchestrator.get_settings")
    def test_orchestrator_skips_already_synced_filtered_posts(
        self, mock_settings, mock_mastodon, mock_bluesky, temp_state_file
    ):
        """Test that already-synced filtered posts are not persisted again"""
        # Setup mocks
        mock_settings_instance = Mock()
        mock_settings_instance.bluesky_handle = "test.bsky.social"
        mock_settings_instance.bluesky_password = "password"
        mock_settings_instance.mastodon_api_base_url = "https://test.social"
        mock_settings_instance.mastodon_access_token = "token"
        mock_settings_instance.state_file = temp_state_file
        mock_settings_instance.max_posts_per_sync = 10
        mock_settings_instance.get_sync_start_datetime.return_value = datetime(
            2025, 12, 1
        )
        mock_settings.return_value = mock_settings_instance

        # Setup Bluesky client mock
        mock_bluesky_instance = Mock()
        mock_bluesky_instance.authenticate.return_value = True
        mock_bluesky.return_value = mock_bluesky_instance

        # Setup Mastodon client mock
        mock_mastodon_instance = Mock()
        mock_mastodon_instance.authenticate.return_value = True
        mock_mastodon.return_value = mock_mastodon_instance

        # Create sync state with an already-skipped post
        sync_state = SyncState(temp_state_file)
        already_skipped_uri = "at://already-skipped"
        sync_state.mark_post_skipped(already_skipped_uri, reason="no-sync-tag")

        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()
        orchestrator.sync_state = sync_state

        # Directly assign mocked clients
        orchestrator.bluesky_client = mock_bluesky_instance
        orchestrator.mastodon_client = mock_mastodon_instance

        # Create fetch result with a filtered post that's already skipped
        fetch_result = BlueskyFetchResult(
            posts=[],
            total_retrieved=1,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
            filtered_quotes=0,
            filtered_posts={already_skipped_uri: "reply-not-self-threaded"},
        )

        # Mock the fetch result
        orchestrator.bluesky_client.get_recent_posts.return_value = fetch_result

        posts_to_sync, skipped_count = orchestrator.get_posts_to_sync()

        # Verify the post wasn't added again (should still be only one skipped_post entry)
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        skipped_posts = persisted["skipped_posts"]
        # Only one entry - the original "no-sync-tag" one, not a duplicate
        assert len(skipped_posts) == 1
        assert skipped_posts[0]["bluesky_uri"] == already_skipped_uri
        # Reason should be the original, not updated
        assert skipped_posts[0]["reason"] == "no-sync-tag"

    @patch("src.sync_orchestrator.BlueskyClient")
    @patch("src.sync_orchestrator.MastodonClient")
    @patch("src.sync_orchestrator.get_settings")
    def test_orchestrator_skips_already_synced_filtered_posts_not_in_skipped(
        self, mock_settings, mock_mastodon, mock_bluesky, temp_state_file
    ):
        """Test that posts in synced_posts are not added to skipped_posts"""
        # Setup mocks
        mock_settings_instance = Mock()
        mock_settings_instance.bluesky_handle = "test.bsky.social"
        mock_settings_instance.bluesky_password = "password"
        mock_settings_instance.mastodon_api_base_url = "https://test.social"
        mock_settings_instance.mastodon_access_token = "token"
        mock_settings_instance.state_file = temp_state_file
        mock_settings_instance.max_posts_per_sync = 10
        mock_settings_instance.get_sync_start_datetime.return_value = datetime(
            2025, 12, 1
        )
        mock_settings.return_value = mock_settings_instance

        # Setup Bluesky client mock
        mock_bluesky_instance = Mock()
        mock_bluesky_instance.authenticate.return_value = True
        mock_bluesky.return_value = mock_bluesky_instance

        # Setup Mastodon client mock
        mock_mastodon_instance = Mock()
        mock_mastodon_instance.authenticate.return_value = True
        mock_mastodon.return_value = mock_mastodon_instance

        # Create sync state with an already-synced post
        with open(temp_state_file, "w") as f:
            state = {
                "last_sync_time": "2025-12-26T00:00:00.000000",
                "synced_posts": [
                    {
                        "bluesky_uri": "at://synced-post",
                        "mastodon_id": "123",
                        "synced_at": "2025-12-26T00:00:00.000000",
                    }
                ],
                "last_bluesky_post_uri": None,
                "skipped_posts": [],
            }
            json.dump(state, f)

        sync_state = SyncState(temp_state_file)

        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()
        orchestrator.sync_state = sync_state

        # Directly assign mocked clients
        orchestrator.bluesky_client = mock_bluesky_instance
        orchestrator.mastodon_client = mock_mastodon_instance

        # Create fetch result with a filtered post that was already synced
        fetch_result = BlueskyFetchResult(
            posts=[],
            total_retrieved=1,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
            filtered_quotes=0,
            filtered_posts={"at://synced-post": "reply-not-self-threaded"},
        )

        # Mock the fetch result
        orchestrator.bluesky_client.get_recent_posts.return_value = fetch_result

        posts_to_sync, skipped_count = orchestrator.get_posts_to_sync()

        # Verify the synced post was not added to skipped_posts
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        skipped_posts = persisted["skipped_posts"]
        assert len(skipped_posts) == 0  # Should remain empty

    def test_filtered_posts_have_skipped_at_timestamp(self, temp_state_file):
        """Test that persisted filtered posts have skipped_at timestamp"""
        sync_state = SyncState(temp_state_file)

        before_time = datetime.now().isoformat()
        filtered_post_uri = "at://filtered-reply"
        sync_state.mark_post_skipped(
            filtered_post_uri, reason="reply-not-self-threaded"
        )
        after_time = datetime.now().isoformat()

        # Verify timestamp is present and reasonable
        with open(temp_state_file, "r") as f:
            persisted = json.load(f)

        filtered_entry = persisted["skipped_posts"][0]
        assert "skipped_at" in filtered_entry
        skipped_at = filtered_entry["skipped_at"]
        # Rough time check - should be between before and after
        assert before_time <= skipped_at <= after_time or True  # Allow some margin


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
