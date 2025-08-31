"""
Integration tests for Social Sync

These tests verify that components work together correctly.
They use mocked external dependencies but test real integration between internal components.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bluesky_client import BlueskyFetchResult
from src.config import Settings
from src.sync_orchestrator import SocialSyncOrchestrator
from src.sync_state import SyncState


class TestSyncIntegration:
    """Integration tests for sync workflow"""

    def setup_method(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_sync_state.json")

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
            "STATE_FILE": "test_state.json",
        },
    )
    def test_full_sync_workflow_with_state_persistence(
        self, mock_mastodon_class, mock_bluesky_class
    ):
        """Test complete sync workflow with state persistence"""
        # Mock successful client setup with proper specifications
        mock_bluesky = Mock(spec=["authenticate", "get_recent_posts"])
        mock_bluesky.authenticate.return_value = True
        mock_bluesky.get_recent_posts.return_value = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )
        mock_bluesky_class.return_value = mock_bluesky

        mock_mastodon = Mock(spec=["authenticate", "post_status"])
        mock_mastodon.authenticate.return_value = True
        mock_mastodon_class.return_value = mock_mastodon

        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()

        # Run sync
        result = orchestrator.run_sync()

        # Verify sync completed
        assert result["success"] is True
        assert result["synced_count"] == 0  # No posts to sync
        assert result["total_processed"] == 0

        # Verify state was updated
        status = orchestrator.get_sync_status()
        assert status["last_sync_time"] is not None

    def test_sync_state_persistence_across_instances(self):
        """Test that sync state persists across different instances"""
        # Create first sync state instance
        sync_state1 = SyncState(self.state_file)
        sync_state1.mark_post_synced("at://test-uri", "mastodon-123")
        sync_state1.update_sync_time()

        # Create second instance with same file
        sync_state2 = SyncState(self.state_file)

        # Verify state persisted
        assert sync_state2.is_post_synced("at://test-uri")
        assert (
            sync_state2.get_mastodon_id_for_bluesky_post("at://test-uri")
            == "mastodon-123"
        )
        assert sync_state2.get_last_sync_time() is not None
        assert sync_state2.get_synced_posts_count() == 1

    @patch.dict(
        os.environ,
        {
            "BLUESKY_HANDLE": "test.bsky.social",
            "BLUESKY_PASSWORD": "test-password",
            "MASTODON_ACCESS_TOKEN": "test-token",
            "DRY_RUN": "true",
        },
    )
    def test_config_settings_integration(self):
        """Test that configuration settings are properly integrated"""
        settings = Settings()

        assert settings.bluesky_handle == "test.bsky.social"
        assert settings.dry_run is True
        assert settings.max_posts_per_sync == 10  # actual configured value in .env

        # Test datetime parsing
        sync_start = settings.get_sync_start_datetime()
        assert isinstance(sync_start, datetime)


class TestContentProcessingIntegration:
    """Integration tests for content processing workflows"""

    def setup_method(self):
        """Set up content processing tests"""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.content_processor import ContentProcessor

        self.processor = ContentProcessor()

    def test_full_content_processing_pipeline(self):
        """Test complete content processing from Bluesky to Mastodon format"""
        # Test with complex post containing multiple elements
        text = "Check out this amazing #library! Created by @developer.bsky.social"
        facets = [
            {
                "index": {"byteStart": 21, "byteEnd": 29},
                "features": [
                    {"$type": "app.bsky.richtext.facet#tag", "tag": "library"}
                ],
            },
            {
                "index": {"byteStart": 42, "byteEnd": 62},
                "features": [
                    {"$type": "app.bsky.richtext.facet#mention", "did": "did:plc:test"}
                ],
            },
        ]

        embed = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": "https://github.com/example/library",
                "title": "Amazing Library",
                "description": "A revolutionary new library for developers",
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            text=text, embed=embed, facets=facets, include_image_placeholders=True
        )

        # Verify content was processed correctly
        assert "#library" in result
        assert "@developer.bsky.social" in result
        assert "🔗 Amazing Library" in result
        assert "https://github.com/example/library" in result

    def test_character_limit_with_attribution(self):
        """Test character limit handling with sync attribution"""
        # Create text that would exceed limit with attribution
        base_text = "x" * 480  # 480 chars

        processed = self.processor.process_bluesky_to_mastodon(
            text=base_text, embed=None, facets=[]
        )

        # Add attribution
        with_attribution = self.processor.add_sync_attribution(processed)

        # Should be truncated to fit within 500 chars
        assert len(with_attribution) <= 500
        assert with_attribution.endswith("(via Bluesky 🦋)")


if __name__ == "__main__":
    # Simple test runner for integration tests
    import unittest

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern="test_integration.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
