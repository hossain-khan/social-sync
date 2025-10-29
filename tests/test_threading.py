"""
Integration tests for threading functionality in Social Sync

These tests verify that threaded post synchronization works correctly,
including reply detection, parent post lookup, and Mastodon reply posting.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bluesky_client import BlueskyPost
from src.sync_orchestrator import SocialSyncOrchestrator
from src.sync_state import SyncState


class TestThreadingSyncFlow:
    """Test threading functionality in sync workflow"""

    def setup_method(self):
        """Set up threading test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "threading_test_state.json")

    def teardown_method(self):
        """Clean up test environment"""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("src.sync_orchestrator.BlueskyClient")
    @patch("src.sync_orchestrator.MastodonClient")
    @patch.dict(
        os.environ,
        {
            "BLUESKY_HANDLE": "test.bsky.social",
            "BLUESKY_PASSWORD": "test-password",
            "MASTODON_API_BASE_URL": "https://mastodon.social",
            "MASTODON_ACCESS_TOKEN": "test-token",
        },
    )
    def test_threading_parent_then_reply_sequence(
        self, mock_mastodon_class, mock_bluesky_class
    ):
        """Test syncing parent post followed by reply post"""
        # Mock client setup
        mock_bluesky = Mock()
        mock_bluesky.authenticate.return_value = True
        mock_bluesky_class.return_value = mock_bluesky

        mock_mastodon = Mock()
        mock_mastodon.authenticate.return_value = True
        mock_mastodon.post_status.side_effect = [
            {"id": "mastodon-parent-id"},
            {"id": "mastodon-reply-id"},
        ]
        mock_mastodon_class.return_value = mock_mastodon

        # Create orchestrator with test state file
        with patch("src.sync_orchestrator.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.bluesky_handle = "test.bsky.social"
            mock_settings.bluesky_password = "test-password"
            mock_settings.mastodon_api_base_url = "https://mastodon.social"
            mock_settings.mastodon_access_token = "test-token"
            mock_settings.dry_run = False
            mock_settings.state_file = self.state_file
            mock_settings.get_sync_start_datetime.return_value = datetime(2025, 1, 1)
            mock_settings.disable_source_platform = False
            mock_get_settings.return_value = mock_settings

            orchestrator = SocialSyncOrchestrator()
            orchestrator.settings = mock_settings

            # Set up clients directly
            orchestrator.bluesky_client = mock_bluesky
            orchestrator.mastodon_client = mock_mastodon

            # Set up sync state
            orchestrator.sync_state = SyncState(self.state_file)

        # Step 1: Sync parent post
        parent_post = BlueskyPost(
            uri="at://parent-post-uri",
            cid="parent-cid",
            text="This is the parent post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,  # Not a reply
            embed=None,
            facets=[],
        )

        # Mock content processor
        mock_content_processor = Mock()
        mock_content_processor.extract_images_from_embed.return_value = []
        mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "This is the parent post"
        )
        mock_content_processor.add_sync_attribution.return_value = (
            "This is the parent post\n\n(via Bluesky)"
        )
        mock_content_processor.get_content_warning_from_labels.return_value = (
            False,
            None,
        )
        orchestrator.content_processor = mock_content_processor

        # Sync parent post
        result = orchestrator.sync_post(parent_post)
        assert result is True

        # Verify parent was posted without reply parameter
        mock_mastodon.post_status.assert_called_with(
            "This is the parent post\n\n(via Bluesky)",
            in_reply_to_id=None,
            media_ids=None,
            sensitive=False,
            spoiler_text=None,
        )

        # Step 2: Sync reply post
        reply_post = BlueskyPost(
            uri="at://reply-post-uri",
            cid="reply-cid",
            text="This is a reply to the parent",
            created_at=datetime(2025, 1, 1, 11, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://parent-post-uri",  # Reply to parent
            embed=None,
            facets=[],
        )

        # Mock content processing for reply (no attribution for replies)
        mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "This is a reply to the parent"
        )

        # Sync reply post
        result = orchestrator.sync_post(reply_post)
        assert result is True

        # Verify reply was posted with in_reply_to_id
        # Check the call count first
        assert mock_mastodon.post_status.call_count == 2

        # Check the second call (reply) has the right in_reply_to_id
        second_call = mock_mastodon.post_status.call_args_list[1]
        assert second_call.kwargs["in_reply_to_id"] == "mastodon-parent-id"

    def test_sync_state_parent_post_lookup(self):
        """Test sync state parent post lookup functionality"""
        sync_state = SyncState(self.state_file)

        # Add parent post mapping
        sync_state.mark_post_synced("at://parent-uri", "mastodon-parent-123")

        # Test lookup
        parent_id = sync_state.get_mastodon_id_for_bluesky_post("at://parent-uri")
        assert parent_id == "mastodon-parent-123"

        # Test non-existent lookup
        missing_id = sync_state.get_mastodon_id_for_bluesky_post("at://nonexistent-uri")
        assert missing_id is None

    @patch("src.sync_orchestrator.BlueskyClient")
    @patch("src.sync_orchestrator.MastodonClient")
    @patch.dict(
        os.environ,
        {
            "BLUESKY_HANDLE": "test.bsky.social",
            "BLUESKY_PASSWORD": "test-password",
            "MASTODON_ACCESS_TOKEN": "test-token",
        },
    )
    def test_orphaned_reply_handling(self, mock_mastodon_class, mock_bluesky_class):
        """Test handling reply posts when parent isn't synced"""
        # Mock client setup
        mock_bluesky = Mock()
        mock_bluesky.authenticate.return_value = True
        mock_bluesky_class.return_value = mock_bluesky

        mock_mastodon = Mock()
        mock_mastodon.authenticate.return_value = True
        mock_mastodon.post_status.return_value = {"id": "orphan-reply-mastodon-id"}
        mock_mastodon_class.return_value = mock_mastodon

        # Create orchestrator
        with patch("src.sync_orchestrator.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.bluesky_handle = "test.bsky.social"
            mock_settings.bluesky_password = "test-password"
            mock_settings.mastodon_access_token = "test-token"
            mock_settings.dry_run = False
            mock_settings.state_file = self.state_file
            mock_settings.disable_source_platform = False
            mock_get_settings.return_value = mock_settings

            orchestrator = SocialSyncOrchestrator()
            orchestrator.settings = mock_settings

            # Set up clients directly
            orchestrator.bluesky_client = mock_bluesky
            orchestrator.mastodon_client = mock_mastodon

            # Set up sync state
            orchestrator.sync_state = SyncState(self.state_file)

        # Create orphaned reply post (parent not in sync state)
        orphan_reply = BlueskyPost(
            uri="at://orphan-reply-uri",
            cid="orphan-cid",
            text="This is an orphaned reply",
            created_at=datetime(2025, 1, 1, 12, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://missing-parent-uri",  # Parent not synced
            embed=None,
            facets=[],
        )

        # Mock content processor
        mock_content_processor = Mock()
        mock_content_processor.extract_images_from_embed.return_value = []
        mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "This is an orphaned reply"
        )
        mock_content_processor.add_sync_attribution.return_value = (
            "This is an orphaned reply\n\n(via Bluesky)"
        )
        mock_content_processor.get_content_warning_from_labels.return_value = (
            False,
            None,
        )
        orchestrator.content_processor = mock_content_processor

        # Sync orphaned reply
        result = orchestrator.sync_post(orphan_reply)
        assert result is True

        # Verify it was posted as standalone (no in_reply_to_id) with attribution
        mock_mastodon.post_status.assert_called_with(
            "This is an orphaned reply\n\n(via Bluesky)",
            in_reply_to_id=None,
            media_ids=None,
            sensitive=False,
            spoiler_text=None,
        )

    @patch("src.sync_orchestrator.BlueskyClient")
    @patch("src.sync_orchestrator.MastodonClient")
    @patch.dict(
        os.environ,
        {
            "BLUESKY_HANDLE": "test.bsky.social",
            "BLUESKY_PASSWORD": "test-password",
            "MASTODON_ACCESS_TOKEN": "test-token",
            "DRY_RUN": "true",
        },
    )
    def test_threading_in_dry_run_mode(self, mock_mastodon_class, mock_bluesky_class):
        """Test threading behavior in dry-run mode"""
        # Mock client setup
        mock_bluesky = Mock()
        mock_bluesky.authenticate.return_value = True
        mock_bluesky_class.return_value = mock_bluesky

        mock_mastodon = Mock()
        mock_mastodon.authenticate.return_value = True
        mock_mastodon_class.return_value = mock_mastodon

        # Create orchestrator in dry-run mode
        with patch("src.sync_orchestrator.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.bluesky_handle = "test.bsky.social"
            mock_settings.bluesky_password = "test-password"
            mock_settings.mastodon_access_token = "test-token"
            mock_settings.dry_run = True  # DRY RUN MODE
            mock_settings.state_file = self.state_file
            mock_get_settings.return_value = mock_settings

            orchestrator = SocialSyncOrchestrator()
            orchestrator.settings = mock_settings

            # Set up clients directly
            orchestrator.bluesky_client = mock_bluesky
            orchestrator.mastodon_client = mock_mastodon

            # Set up sync state
            orchestrator.sync_state = SyncState(self.state_file)

        # Test reply post in dry-run
        reply_post = BlueskyPost(
            uri="at://dry-run-reply",
            cid="dry-cid",
            text="Dry run reply",
            created_at=datetime(2025, 1, 1, 13, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://some-parent-uri",
            embed=None,
            facets=[],
        )

        # Mock content processor
        mock_content_processor = Mock()
        mock_content_processor.extract_images_from_embed.return_value = []
        mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Dry run reply"
        )
        mock_content_processor.add_sync_attribution.return_value = (
            "Dry run reply\n\n(via Bluesky)"
        )
        mock_content_processor.get_content_warning_from_labels.return_value = (
            False,
            None,
        )
        orchestrator.content_processor = mock_content_processor

        # Sync in dry-run mode
        result = orchestrator.sync_post(reply_post)
        assert result is True

        # Verify no actual posting occurred
        mock_mastodon.post_status.assert_not_called()


class TestThreadingEdgeCases:
    """Test edge cases and error conditions in threading"""

    def test_did_extraction_from_at_uris(self):
        """Test DID extraction from AT Protocol URIs"""
        from src.bluesky_client import BlueskyClient

        # Create client instance
        client = BlueskyClient("test.bsky.social", "password")

        # Test valid DIDs
        test_cases = [
            (
                "at://did:plc:sek23f2vucrxxyaaud2emnxe/app.bsky.feed.post/3lxmsjwv7v22t",
                "did:plc:sek23f2vucrxxyaaud2emnxe",
            ),
            (
                "at://did:plc:abcd1234efgh5678/app.bsky.feed.post/xyz789",
                "did:plc:abcd1234efgh5678",
            ),
            (
                "at://did:web:example.com/app.bsky.feed.post/test123",
                "did:web:example.com",
            ),
        ]

        for uri, expected_did in test_cases:
            result = client._extract_did_from_uri(uri)
            assert result == expected_did, f"Failed to extract DID from: {uri}"

        # Test invalid cases
        invalid_cases = [
            "",  # Empty string
            "not-an-at-uri",  # No at:// prefix
            "at://not-a-did/path",  # Invalid DID format
            "at://did/incomplete",  # Incomplete DID
            "at://did:plc:/path",  # Empty DID identifier
        ]

        for invalid_uri in invalid_cases:
            result = client._extract_did_from_uri(invalid_uri)
            assert result is None, f"Should return None for invalid URI: {invalid_uri}"

    def test_reply_to_field_extraction(self):
        """Test various reply_to field formats"""
        # Test with AT URI format
        post_with_reply = BlueskyPost(
            uri="at://test-reply",
            cid="test-cid",
            text="Reply text",
            created_at=datetime.now(),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://did:plc:parent123/app.bsky.feed.post/abc123",
            embed=None,
            facets=[],
        )

        assert (
            post_with_reply.reply_to
            == "at://did:plc:parent123/app.bsky.feed.post/abc123"
        )

        # Test with None (not a reply)
        regular_post = BlueskyPost(
            uri="at://test-regular",
            cid="test-cid",
            text="Regular text",
            created_at=datetime.now(),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        assert regular_post.reply_to is None

    def test_sync_state_thread_mappings(self):
        """Test sync state handles thread mappings correctly"""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()

        try:
            sync_state = SyncState(temp_file.name)

            # Add thread: parent -> reply1 -> reply2
            sync_state.mark_post_synced("at://parent", "mastodon-parent")
            sync_state.mark_post_synced("at://reply1", "mastodon-reply1")
            sync_state.mark_post_synced("at://reply2", "mastodon-reply2")

            # Verify all mappings exist
            assert (
                sync_state.get_mastodon_id_for_bluesky_post("at://parent")
                == "mastodon-parent"
            )
            assert (
                sync_state.get_mastodon_id_for_bluesky_post("at://reply1")
                == "mastodon-reply1"
            )
            assert (
                sync_state.get_mastodon_id_for_bluesky_post("at://reply2")
                == "mastodon-reply2"
            )

            # Verify count
            assert sync_state.get_synced_posts_count() == 3

        finally:
            os.unlink(temp_file.name)


if __name__ == "__main__":
    # Simple test runner for threading tests
    import unittest

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern="test_threading.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
