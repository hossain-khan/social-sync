"""
Tests for Sync Orchestrator
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.bluesky_client import BlueskyFetchResult, BlueskyPost
from src.sync_orchestrator import SocialSyncOrchestrator


class TestSocialSyncOrchestrator:
    """Test suite for SocialSyncOrchestrator class"""

    def setup_method(self):
        """Set up test fixtures with mocked dependencies"""
        # Start patches that will last for the entire test method
        self.settings_patcher = patch("src.sync_orchestrator.get_settings")
        self.bluesky_patcher = patch("src.sync_orchestrator.BlueskyClient")
        self.mastodon_patcher = patch("src.sync_orchestrator.MastodonClient")
        self.sync_state_patcher = patch("src.sync_orchestrator.SyncState")
        self.content_processor_patcher = patch("src.sync_orchestrator.ContentProcessor")

        mock_get_settings = self.settings_patcher.start()
        self.mock_bluesky_class = self.bluesky_patcher.start()
        self.mock_mastodon_class = self.mastodon_patcher.start()
        self.mock_sync_state_class = self.sync_state_patcher.start()
        self.mock_content_processor_class = self.content_processor_patcher.start()

        # Mock settings with proper specification
        mock_settings = Mock(
            spec=[
                "bluesky_handle",
                "bluesky_password",
                "mastodon_api_base_url",
                "mastodon_access_token",
                "max_posts_per_sync",
                "dry_run",
                "state_file",
                "get_sync_start_datetime",
                "disable_source_platform",
            ]
        )
        mock_settings.bluesky_handle = "test.bsky.social"
        mock_settings.bluesky_password = "test-password"
        mock_settings.mastodon_api_base_url = "https://mastodon.social"
        mock_settings.mastodon_access_token = "test-token"
        mock_settings.max_posts_per_sync = 10
        mock_settings.dry_run = False
        mock_settings.state_file = "test_state.json"
        mock_settings.get_sync_start_datetime.return_value = datetime(2025, 1, 1)
        mock_settings.disable_source_platform = False
        mock_get_settings.return_value = mock_settings

        # Mock client instances with proper specifications
        self.mock_bluesky_client = Mock(
            spec=[
                "authenticate",
                "get_recent_posts",
                "get_post_thread",
                "download_blob",
            ]
        )
        self.mock_mastodon_client = Mock(
            spec=["authenticate", "post_status", "upload_media"]
        )
        self.mock_sync_state = Mock(
            spec=[
                "is_post_synced",
                "mark_post_synced",
                "is_post_skipped",
                "mark_post_skipped",
                "get_mastodon_id_for_bluesky_post",
                "get_last_sync_time",
                "update_sync_time",
                "get_synced_posts_count",
                "get_skipped_posts_count",
                "cleanup_old_records",
            ]
        )
        self.mock_content_processor = Mock(
            spec=[
                "process_bluesky_to_mastodon",
                "download_image",
                "extract_images_from_embed",
                "add_sync_attribution",
                "has_no_sync_tag",
            ]
        )

        self.mock_bluesky_class.return_value = self.mock_bluesky_client
        self.mock_mastodon_class.return_value = self.mock_mastodon_client
        self.mock_sync_state_class.return_value = self.mock_sync_state
        self.mock_content_processor_class.return_value = self.mock_content_processor

        self.orchestrator = SocialSyncOrchestrator()

    def teardown_method(self):
        """Clean up patches after each test"""
        self.settings_patcher.stop()
        self.bluesky_patcher.stop()
        self.mastodon_patcher.stop()
        self.sync_state_patcher.stop()
        self.content_processor_patcher.stop()

    def test_setup_clients_success(self):
        """Test successful client setup"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True

        result = self.orchestrator.setup_clients()

        assert result is True
        self.mock_bluesky_client.authenticate.assert_called_once()
        self.mock_mastodon_client.authenticate.assert_called_once()

    def test_setup_clients_bluesky_auth_failure(self):
        """Test client setup with Bluesky authentication failure"""
        self.mock_bluesky_client.authenticate.return_value = False
        self.mock_mastodon_client.authenticate.return_value = True

        result = self.orchestrator.setup_clients()

        assert result is False
        self.mock_bluesky_client.authenticate.assert_called_once()
        # Mastodon client should not be called if Bluesky fails
        self.mock_mastodon_client.authenticate.assert_not_called()

    def test_setup_clients_mastodon_auth_failure(self):
        """Test client setup with Mastodon authentication failure"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = False

        result = self.orchestrator.setup_clients()

        assert result is False
        self.mock_bluesky_client.authenticate.assert_called_once()
        self.mock_mastodon_client.authenticate.assert_called_once()

    def test_get_posts_to_sync_no_posts(self):
        """Test getting posts when no posts are available"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        self.mock_bluesky_client.get_recent_posts.return_value = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        result = self.orchestrator.get_posts_to_sync()

        assert result == []
        self.mock_bluesky_client.get_recent_posts.assert_called_once()

    def test_get_posts_to_sync_with_new_posts(self):
        """Test getting posts with new (unsynced) posts"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        # Mock posts from Bluesky
        mock_post1 = BlueskyPost(
            uri="at://test-uri-1",
            cid="test-cid-1",
            text="Test post 1",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        mock_post2 = BlueskyPost(
            uri="at://test-uri-2",
            cid="test-cid-2",
            text="Test post 2",
            created_at=datetime(2025, 1, 1, 11, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        self.mock_bluesky_client.get_recent_posts.return_value = BlueskyFetchResult(
            posts=[mock_post1, mock_post2],
            total_retrieved=2,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )
        self.mock_sync_state.is_post_synced.return_value = (
            False  # Neither post is synced
        )
        self.mock_sync_state.is_post_skipped.return_value = False
        self.mock_content_processor.has_no_sync_tag.return_value = False

        result = self.orchestrator.get_posts_to_sync()

        assert len(result) == 2
        assert result[0].uri == "at://test-uri-1"  # Should be sorted by creation time
        assert result[1].uri == "at://test-uri-2"

    def test_get_posts_to_sync_filter_already_synced(self):
        """Test getting posts filters out already synced posts"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post1 = BlueskyPost(
            uri="at://synced-uri",
            cid="test-cid-1",
            text="Already synced post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        mock_post2 = BlueskyPost(
            uri="at://new-uri",
            cid="test-cid-2",
            text="New post",
            created_at=datetime(2025, 1, 1, 11, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        self.mock_bluesky_client.get_recent_posts.return_value = BlueskyFetchResult(
            posts=[mock_post1, mock_post2],
            total_retrieved=2,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        # Mock sync state: first post is synced, second is not
        def is_post_synced_side_effect(uri):
            return uri == "at://synced-uri"

        self.mock_sync_state.is_post_synced.side_effect = is_post_synced_side_effect
        self.mock_sync_state.is_post_skipped.return_value = False
        self.mock_content_processor.has_no_sync_tag.return_value = False

        result = self.orchestrator.get_posts_to_sync()

        assert len(result) == 1
        assert result[0].uri == "at://new-uri"

    def test_get_posts_to_sync_with_logging_stats(self):
        """Test getting posts with logging stats triggered"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        self.mock_bluesky_client.get_recent_posts.return_value = BlueskyFetchResult(
            posts=[],
            total_retrieved=10,
            filtered_replies=2,
            filtered_reposts=3,
            filtered_by_date=1,
        )
        self.mock_sync_state.is_post_synced.return_value = False
        self.mock_sync_state.is_post_skipped.return_value = False
        self.mock_content_processor.has_no_sync_tag.return_value = False

        # We don't need to check the result, just that the method runs without error
        # and the logging lines are covered.
        self.orchestrator.get_posts_to_sync()

        self.mock_bluesky_client.get_recent_posts.assert_called_once()

    def test_sync_post_simple_text_success(self):
        """Test syncing a simple text post successfully"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://test-uri",
            cid="test-cid",
            text="Simple test post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text\n\n(via Bluesky)"
        )

        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = {
            "id": "mastodon-post-id-123"
        }

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_mastodon_client.post_status.assert_called_once()
        self.mock_sync_state.mark_post_synced.assert_called_once_with(
            "at://test-uri", "mastodon-post-id-123"
        )

    def test_sync_post_reply_with_parent_found(self):
        """Test syncing a reply post when parent is found"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://reply-uri",
            cid="test-cid",
            text="This is a reply",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://parent-uri",
            embed=None,
            facets=[],
        )

        # Mock finding parent post
        self.mock_sync_state.get_mastodon_id_for_bluesky_post.return_value = (
            "parent-mastodon-id"
        )

        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "This is a reply"
        )
        # Note: replies don't get sync attribution

        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = {"id": "reply-mastodon-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        # Verify post_status called with in_reply_to_id
        self.mock_mastodon_client.post_status.assert_called_once()
        call_args = self.mock_mastodon_client.post_status.call_args
        assert call_args[1]["in_reply_to_id"] == "parent-mastodon-id"

    def test_sync_post_reply_parent_not_found(self):
        """Test syncing a reply post when parent is not found"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://orphan-reply-uri",
            cid="test-cid",
            text="Orphaned reply",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://missing-parent-uri",
            embed=None,
            facets=[],
        )

        # Mock parent not found
        self.mock_sync_state.get_mastodon_id_for_bluesky_post.return_value = None

        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Orphaned reply"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Orphaned reply\n\n(via Bluesky)"
        )

        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = {
            "id": "orphan-mastodon-id"
        }

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        # Should post as standalone (no in_reply_to_id)
        call_args = self.mock_mastodon_client.post_status.call_args
        assert (
            "in_reply_to_id" not in call_args[1]
            or call_args[1]["in_reply_to_id"] is None
        )

    def test_sync_post_dry_run_mode(self):
        """Test syncing a post in dry-run mode"""
        self.orchestrator.settings.dry_run = True

        mock_post = BlueskyPost(
            uri="at://dry-run-uri",
            cid="test-cid",
            text="Dry run post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Dry run post"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Dry run post\n\n(via Bluesky)"
        )

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        # Should not actually post to Mastodon in dry-run
        self.mock_mastodon_client.post_status.assert_not_called()
        # Should not mark as synced in dry-run
        self.mock_sync_state.mark_post_synced.assert_not_called()

    def test_sync_post_mastodon_error(self):
        """Test syncing a post when Mastodon posting fails"""
        mock_post = BlueskyPost(
            uri="at://error-uri",
            cid="test-cid",
            text="Error post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Error post"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Error post\n\n(via Bluesky)"
        )

        # Mock Mastodon posting failure
        self.mock_mastodon_client.post_status.side_effect = Exception(
            "Mastodon API error"
        )

        result = self.orchestrator.sync_post(mock_post)

        assert result is False
        # Should not mark as synced if posting fails
        self.mock_sync_state.mark_post_synced.assert_not_called()

    def test_sync_post_with_image_success(self):
        """Test syncing a post with an image successfully"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://did:plc:123/app.bsky.feed.post/abc",
            cid="test-cid",
            text="Post with image",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed={"images": [{"blob_ref": "blob1", "alt": "alt text"}]},
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"blob_ref": "blob1", "alt": "alt text"}
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text with attribution"
        )
        self.mock_bluesky_client.download_blob.return_value = (
            b"imagedata",
            "image/jpeg",
        )
        self.mock_mastodon_client.upload_media.return_value = "media-id-1"
        self.mock_mastodon_client.post_status.return_value = {"id": "mastodon-post-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_bluesky_client.download_blob.assert_called_once()
        self.mock_mastodon_client.upload_media.assert_called_once()
        self.mock_mastodon_client.post_status.assert_called_once_with(
            "Processed text with attribution",
            in_reply_to_id=None,
            media_ids=["media-id-1"],
        )
        self.mock_sync_state.mark_post_synced.assert_called_once()

    def test_sync_post_with_image_from_url_success(self):
        """Test syncing a post with an image from a URL successfully"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://did:plc:123/app.bsky.feed.post/abc",
            cid="test-cid",
            text="Post with image from URL",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed={
                "images": [{"url": "http://example.com/image.jpg", "alt": "alt text"}]
            },
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"url": "http://example.com/image.jpg", "alt": "alt text"}
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text with attribution"
        )
        self.mock_content_processor.download_image.return_value = (
            b"imagedata",
            "image/jpeg",
        )
        self.mock_mastodon_client.upload_media.return_value = "media-id-1"
        self.mock_mastodon_client.post_status.return_value = {"id": "mastodon-post-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_content_processor.download_image.assert_called_once()
        self.mock_mastodon_client.upload_media.assert_called_once()
        self.mock_mastodon_client.post_status.assert_called_once_with(
            "Processed text with attribution",
            in_reply_to_id=None,
            media_ids=["media-id-1"],
        )
        self.mock_sync_state.mark_post_synced.assert_called_once()

    def test_sync_post_with_multiple_images(self):
        """Test syncing a post with multiple images"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://did:plc:123/app.bsky.feed.post/abc",
            cid="test-cid",
            text="Post with multiple images",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed={
                "images": [
                    {"blob_ref": "blob1", "alt": "alt1"},
                    {"blob_ref": "blob2", "alt": "alt2"},
                ]
            },
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"blob_ref": "blob1", "alt": "alt1"},
            {"blob_ref": "blob2", "alt": "alt2"},
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text with attribution"
        )
        self.mock_bluesky_client.download_blob.side_effect = [
            (b"imagedata1", "image/jpeg"),
            (b"imagedata2", "image/png"),
        ]
        self.mock_mastodon_client.upload_media.side_effect = [
            "media-id-1",
            "media-id-2",
        ]
        self.mock_mastodon_client.post_status.return_value = {"id": "mastodon-post-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        assert self.mock_bluesky_client.download_blob.call_count == 2
        assert self.mock_mastodon_client.upload_media.call_count == 2
        self.mock_mastodon_client.post_status.assert_called_once_with(
            "Processed text with attribution",
            in_reply_to_id=None,
            media_ids=["media-id-1", "media-id-2"],
        )

    def test_sync_post_image_download_fails(self):
        """Test syncing a post where image download fails"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://did:plc:123/app.bsky.feed.post/abc",
            cid="test-cid",
            text="Post with failing image",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed={"images": [{"blob_ref": "blob1", "alt": "alt text"}]},
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"blob_ref": "blob1", "alt": "alt text"}
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text with attribution"
        )
        self.mock_bluesky_client.download_blob.return_value = None  # Download fails
        self.mock_mastodon_client.post_status.return_value = {"id": "mastodon-post-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_mastodon_client.upload_media.assert_not_called()
        # Should post without media
        self.mock_mastodon_client.post_status.assert_called_once_with(
            "Processed text with attribution",
            in_reply_to_id=None,
            media_ids=None,
        )

    def test_sync_post_image_upload_fails(self):
        """Test syncing a post where image upload fails"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://did:plc:123/app.bsky.feed.post/abc",
            cid="test-cid",
            text="Post with failing upload",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed={"images": [{"blob_ref": "blob1", "alt": "alt text"}]},
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"blob_ref": "blob1", "alt": "alt text"}
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text with attribution"
        )
        self.mock_bluesky_client.download_blob.return_value = (
            b"imagedata",
            "image/jpeg",
        )
        self.mock_mastodon_client.upload_media.return_value = None  # Upload fails
        self.mock_mastodon_client.post_status.return_value = {"id": "mastodon-post-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_mastodon_client.upload_media.assert_called_once()
        # Should post without media since upload failed
        self.mock_mastodon_client.post_status.assert_called_once_with(
            "Processed text with attribution",
            in_reply_to_id=None,
            media_ids=None,
        )

    def test_sync_post_with_image_dry_run(self):
        """Test syncing a post with an image in dry-run mode"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()
        self.orchestrator.settings.dry_run = True

        mock_post = BlueskyPost(
            uri="at://dry-run-uri",
            cid="test-cid",
            text="Dry run with image",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed={"images": [{"blob_ref": "blob1", "alt": "alt text"}]},
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"blob_ref": "blob1", "alt": "alt text"}
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text with attribution"
        )

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_bluesky_client.download_blob.assert_not_called()
        self.mock_mastodon_client.upload_media.assert_not_called()
        self.mock_mastodon_client.post_status.assert_not_called()
        self.mock_sync_state.mark_post_synced.assert_not_called()

    def test_sync_post_reply_with_parent_and_image(self):
        """Test syncing a reply with an image when parent is found"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://did:plc:123/app.bsky.feed.post/reply",
            cid="test-cid-reply",
            text="Reply with image",
            created_at=datetime(2025, 1, 1, 11, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://parent-uri",
            embed={"images": [{"blob_ref": "blob1", "alt": "alt text"}]},
            facets=[],
        )

        self.mock_sync_state.get_mastodon_id_for_bluesky_post.return_value = (
            "parent-mastodon-id"
        )
        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"blob_ref": "blob1", "alt": "alt text"}
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed reply text"
        )
        self.mock_bluesky_client.download_blob.return_value = (
            b"imagedata",
            "image/jpeg",
        )
        self.mock_mastodon_client.upload_media.return_value = "media-id-1"
        self.mock_mastodon_client.post_status.return_value = {"id": "mastodon-reply-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_mastodon_client.post_status.assert_called_once_with(
            "Processed reply text",
            in_reply_to_id="parent-mastodon-id",
            media_ids=["media-id-1"],
        )
        # Attribution should not be added to replies
        self.mock_content_processor.add_sync_attribution.assert_not_called()

    def test_sync_image_download_exception(self):
        """Test that an exception during image download is handled."""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://did:plc:123/app.bsky.feed.post/abc",
            cid="test-cid",
            text="Post with failing image",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed={"images": [{"blob_ref": "blob1", "alt": "alt text"}]},
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = [
            {"blob_ref": "blob1", "alt": "alt text"}
        ]
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Processed text"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Processed text with attribution"
        )
        self.mock_bluesky_client.download_blob.side_effect = Exception("Download error")
        self.mock_mastodon_client.post_status.return_value = {"id": "mastodon-post-id"}

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        self.mock_mastodon_client.upload_media.assert_not_called()
        self.mock_mastodon_client.post_status.assert_called_once_with(
            "Processed text with attribution",
            in_reply_to_id=None,
            media_ids=None,
        )

    def test_run_sync_success(self):
        """Test successful sync run"""
        # Mock client setup
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True

        # Mock posts to sync
        mock_posts = [
            BlueskyPost(
                uri="at://post-1",
                cid="cid-1",
                text="Post 1",
                created_at=datetime(2025, 1, 1, 10, 0),
                author_handle="test.bsky.social",
                author_display_name="Test User",
                reply_to=None,
                embed=None,
                facets=[],
            ),
            BlueskyPost(
                uri="at://post-2",
                cid="cid-2",
                text="Post 2",
                created_at=datetime(2025, 1, 1, 11, 0),
                author_handle="test.bsky.social",
                author_display_name="Test User",
                reply_to=None,
                embed=None,
                facets=[],
            ),
        ]

        self.mock_bluesky_client.get_recent_posts.return_value = BlueskyFetchResult(
            posts=mock_posts,
            total_retrieved=2,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )
        self.mock_sync_state.is_post_synced.return_value = False
        self.mock_sync_state.is_post_skipped.return_value = False
        self.mock_content_processor.has_no_sync_tag.return_value = False

        # Mock successful sync for both posts
        with patch.object(
            self.orchestrator, "sync_post", return_value=True
        ) as mock_sync_post:
            result = self.orchestrator.run_sync()

        assert result["success"] is True
        assert result["synced_count"] == 2
        assert result["failed_count"] == 0
        assert result["total_processed"] == 2
        assert result["dry_run"] is False
        assert isinstance(result["duration"], float)

        # Verify sync_post called for both posts
        assert mock_sync_post.call_count == 2
        self.mock_sync_state.update_sync_time.assert_called_once()
        self.mock_sync_state.cleanup_old_records.assert_called_once()

    def test_run_sync_client_setup_failure(self):
        """Test sync run with client setup failure"""
        self.mock_bluesky_client.authenticate.return_value = False

        result = self.orchestrator.run_sync()

        assert result["success"] is False
        assert result["error"] == "Failed to setup clients"
        assert result["synced_count"] == 0
        assert isinstance(result["duration"], float)

    def test_run_sync_no_posts(self):
        """Test sync run when no posts are available"""
        # Mock client setup success
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True

        # Mock no posts to sync
        self.mock_bluesky_client.get_recent_posts.return_value = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        result = self.orchestrator.run_sync()

        assert result["success"] is True
        assert result["synced_count"] == 0
        assert result["failed_count"] == 0
        assert result["total_processed"] == 0

        # Should still update sync time even with no posts
        self.mock_sync_state.update_sync_time.assert_called_once()

    def test_sync_post_mastodon_falsy_response(self):
        """Test syncing a post when Mastodon returns a falsy response (e.g. None)"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://error-uri",
            cid="test-cid",
            text="Error post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Error post"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Error post\n\n(via Bluesky)"
        )
        self.mock_mastodon_client.post_status.return_value = None

        result = self.orchestrator.sync_post(mock_post)

        assert result is False
        self.mock_sync_state.mark_post_synced.assert_not_called()

    def test_run_sync_get_posts_error(self):
        """Test sync run with an error during post fetching"""
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.mock_bluesky_client.get_recent_posts.side_effect = Exception(
            "API fetch error"
        )

        result = self.orchestrator.run_sync()

        assert result["success"] is False
        assert "Failed to get posts" in result["error"]
        assert result["synced_count"] == 0

    def test_run_sync_partial_failure(self):
        """Test sync run with some posts failing"""
        # Mock client setup
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True

        # Mock posts to sync
        mock_posts = [
            BlueskyPost(
                uri="at://success-post",
                cid="cid-1",
                text="Success post",
                created_at=datetime(2025, 1, 1, 10, 0),
                author_handle="test.bsky.social",
                author_display_name="Test User",
                reply_to=None,
                embed=None,
                facets=[],
            ),
            BlueskyPost(
                uri="at://fail-post",
                cid="cid-2",
                text="Fail post",
                created_at=datetime(2025, 1, 1, 11, 0),
                author_handle="test.bsky.social",
                author_display_name="Test User",
                reply_to=None,
                embed=None,
                facets=[],
            ),
        ]

        self.mock_bluesky_client.get_recent_posts.return_value = BlueskyFetchResult(
            posts=mock_posts,
            total_retrieved=2,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )
        self.mock_sync_state.is_post_synced.return_value = False
        self.mock_sync_state.is_post_skipped.return_value = False
        self.mock_content_processor.has_no_sync_tag.return_value = False

        # Mock mixed success/failure
        def sync_post_side_effect(post):
            return post.uri == "at://success-post"

        with patch.object(
            self.orchestrator, "sync_post", side_effect=sync_post_side_effect
        ):
            result = self.orchestrator.run_sync()

        assert result["success"] is True
        assert result["synced_count"] == 1
        assert result["failed_count"] == 1
        assert result["total_processed"] == 2

    def test_get_sync_status(self):
        """Test getting sync status"""
        # Mock sync state
        mock_last_sync = datetime(2025, 1, 1, 12, 0)
        self.mock_sync_state.get_last_sync_time.return_value = mock_last_sync
        self.mock_sync_state.get_synced_posts_count.return_value = 42

        result = self.orchestrator.get_sync_status()

        assert result["last_sync_time"] == mock_last_sync.isoformat()
        assert result["total_synced_posts"] == 42
        assert result["dry_run_mode"] is False

    def test_get_sync_status_no_previous_sync(self):
        """Test getting sync status when no previous sync exists"""
        self.mock_sync_state.get_last_sync_time.return_value = None
        self.mock_sync_state.get_synced_posts_count.return_value = 0

        result = self.orchestrator.get_sync_status()

        assert result["last_sync_time"] is None
        assert result["total_synced_posts"] == 0
        assert result["dry_run_mode"] is False

    def test_sync_post_with_disable_source_platform(self):
        """Test that source platform attribution is not added when disabled"""
        # Enable disable_source_platform setting
        self.orchestrator.settings.disable_source_platform = True

        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://test-uri-no-attribution",
            cid="test-cid",
            text="Post without attribution",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Post without attribution"
        )

        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = {
            "id": "mastodon-post-id-no-attr"
        }

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        # Verify add_sync_attribution was NOT called when disable_source_platform is True
        self.mock_content_processor.add_sync_attribution.assert_not_called()
        self.mock_mastodon_client.post_status.assert_called_once()
        self.mock_sync_state.mark_post_synced.assert_called_once_with(
            "at://test-uri-no-attribution", "mastodon-post-id-no-attr"
        )

    def test_sync_post_with_source_platform_enabled(self):
        """Test that source platform attribution IS added when enabled (default)"""
        # Ensure disable_source_platform is False (default)
        self.orchestrator.settings.disable_source_platform = False

        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        mock_post = BlueskyPost(
            uri="at://test-uri-with-attribution",
            cid="test-cid",
            text="Post with attribution",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[],
        )

        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = (
            "Post with attribution"
        )
        self.mock_content_processor.add_sync_attribution.return_value = (
            "Post with attribution\n\n(via Bluesky 🦋)"
        )

        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = {
            "id": "mastodon-post-id-with-attr"
        }

        result = self.orchestrator.sync_post(mock_post)

        assert result is True
        # Verify add_sync_attribution WAS called when disable_source_platform is False
        self.mock_content_processor.add_sync_attribution.assert_called_once_with(
            "Post with attribution"
        )
        self.mock_mastodon_client.post_status.assert_called_once()
        self.mock_sync_state.mark_post_synced.assert_called_once_with(
            "at://test-uri-with-attribution", "mastodon-post-id-with-attr"
        )

    def test_get_posts_to_sync_filters_no_sync_tag(self):
        """Test that posts with #no-sync tag are filtered out"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        # Mock sync state
        self.mock_sync_state.is_post_synced.return_value = False
        self.mock_sync_state.is_post_skipped.return_value = False

        # Mock content processor to detect #no-sync tag
        def has_no_sync_tag_side_effect(text):
            return "#no-sync" in text.lower()

        self.mock_content_processor.has_no_sync_tag.side_effect = (
            has_no_sync_tag_side_effect
        )

        # Create test posts - one with #no-sync tag and one without
        mock_posts = [
            BlueskyPost(
                uri="at://post-normal",
                cid="cid1",
                text="This is a normal post",
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
            BlueskyPost(
                uri="at://post-with-no-sync",
                cid="cid2",
                text="This post should be skipped #no-sync",
                created_at=datetime(2024, 1, 1, 12, 5, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
            BlueskyPost(
                uri="at://post-another-normal",
                cid="cid3",
                text="Another normal post",
                created_at=datetime(2024, 1, 1, 12, 10, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
        ]

        fetch_result = BlueskyFetchResult(
            posts=mock_posts,
            total_retrieved=3,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        self.mock_bluesky_client.get_recent_posts.return_value = fetch_result

        # Get posts to sync
        posts = self.orchestrator.get_posts_to_sync()

        # Should only return 2 posts (skipping the one with #no-sync tag)
        assert len(posts) == 2
        assert posts[0].uri == "at://post-normal"
        assert posts[1].uri == "at://post-another-normal"

        # Verify that mark_post_skipped was called for the #no-sync post
        self.mock_sync_state.mark_post_skipped.assert_called_once_with(
            "at://post-with-no-sync", reason="no-sync-tag"
        )

    def test_get_posts_to_sync_already_skipped_posts(self):
        """Test that already skipped posts are not processed again"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        def is_post_skipped_side_effect(uri):
            return uri == "at://post-already-skipped"

        self.mock_sync_state.is_post_synced.return_value = False
        self.mock_sync_state.is_post_skipped.side_effect = is_post_skipped_side_effect
        self.mock_content_processor.has_no_sync_tag.return_value = False

        # Create test posts - one that was already skipped
        mock_posts = [
            BlueskyPost(
                uri="at://post-normal",
                cid="cid1",
                text="This is a normal post",
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
            BlueskyPost(
                uri="at://post-already-skipped",
                cid="cid2",
                text="This was skipped before #no-sync",
                created_at=datetime(2024, 1, 1, 12, 5, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
        ]

        fetch_result = BlueskyFetchResult(
            posts=mock_posts,
            total_retrieved=2,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        self.mock_bluesky_client.get_recent_posts.return_value = fetch_result

        # Get posts to sync
        posts = self.orchestrator.get_posts_to_sync()

        # Should only return 1 post (the normal one)
        assert len(posts) == 1
        assert posts[0].uri == "at://post-normal"

        # Verify that mark_post_skipped was NOT called (already skipped)
        self.mock_sync_state.mark_post_skipped.assert_not_called()

    def test_get_sync_status_includes_skipped_posts(self):
        """Test that sync status includes skipped posts count"""
        # Mock the state methods
        self.mock_sync_state.get_last_sync_time.return_value = datetime(
            2024, 1, 1, 12, 0, 0
        )
        self.mock_sync_state.get_synced_posts_count.return_value = 42
        self.mock_sync_state.get_skipped_posts_count.return_value = 5

        status = self.orchestrator.get_sync_status()

        assert status["total_synced_posts"] == 42
        assert status["total_skipped_posts"] == 5
        assert "total_skipped_posts" in status

    def test_no_sync_tag_case_variations(self):
        """Test that #no-sync tag is detected with various case variations"""
        # Set up clients first
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        self.orchestrator.setup_clients()

        self.mock_sync_state.is_post_synced.return_value = False
        self.mock_sync_state.is_post_skipped.return_value = False

        # Use actual ContentProcessor for this test
        from src.content_processor import ContentProcessor

        real_processor = ContentProcessor()
        self.orchestrator.content_processor = real_processor

        # Create test posts with different case variations
        mock_posts = [
            BlueskyPost(
                uri="at://post-lowercase",
                cid="cid1",
                text="Post with #no-sync",
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
            BlueskyPost(
                uri="at://post-uppercase",
                cid="cid2",
                text="Post with #NO-SYNC",
                created_at=datetime(2024, 1, 1, 12, 5, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
            BlueskyPost(
                uri="at://post-mixedcase",
                cid="cid3",
                text="Post with #No-Sync",
                created_at=datetime(2024, 1, 1, 12, 10, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
            BlueskyPost(
                uri="at://post-normal",
                cid="cid4",
                text="Normal post without tag",
                created_at=datetime(2024, 1, 1, 12, 15, 0),
                author_handle="user.bsky.social",
                reply_to=None,
            ),
        ]

        fetch_result = BlueskyFetchResult(
            posts=mock_posts,
            total_retrieved=4,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        self.mock_bluesky_client.get_recent_posts.return_value = fetch_result

        # Get posts to sync
        posts = self.orchestrator.get_posts_to_sync()

        # Should only return the normal post
        assert len(posts) == 1
        assert posts[0].uri == "at://post-normal"

        # Verify all three #no-sync variations were marked as skipped
        assert self.mock_sync_state.mark_post_skipped.call_count == 3
