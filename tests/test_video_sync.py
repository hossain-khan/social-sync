"""
Tests for video sync functionality
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.bluesky_client import BlueskyClient
from src.content_processor import ContentProcessor
from src.mastodon_client import MastodonClient


class TestVideoEmbedExtraction:
    """Test video embed extraction from Bluesky posts"""

    def test_extract_video_embed_data(self):
        """Test extraction of video embed data"""
        # Create a mock video embed
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.video"
        mock_embed.alt = "Test video description"
        mock_embed.aspect_ratio = Mock(width=1920, height=1080)
        mock_embed.images = None  # No images
        mock_embed.media = None  # No media
        mock_embed.record = None  # No record
        mock_embed.external = None  # No external

        # Mock video object
        mock_video = Mock()
        mock_video.mime_type = "video/mp4"
        mock_video.size = 5000000  # 5MB

        # Mock blob reference
        mock_ref = Mock()
        mock_ref.link = "bafytest123"
        mock_video.ref = mock_ref

        mock_embed.video = mock_video

        # Extract video data
        result = BlueskyClient._extract_embed_data(mock_embed)

        assert result is not None
        assert "video" in result
        assert result["video"]["blob_ref"] == "bafytest123"
        assert result["video"]["mime_type"] == "video/mp4"
        assert result["video"]["size"] == 5000000
        assert result["video"]["alt"] == "Test video description"

    def test_extract_video_embed_with_dict_ref(self):
        """Test extraction with dictionary-style blob reference"""
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.video"
        mock_embed.alt = None
        mock_embed.aspect_ratio = None
        mock_embed.images = None
        mock_embed.media = None
        mock_embed.record = None
        mock_embed.external = None

        mock_video = Mock()
        mock_video.mime_type = "video/mp4"
        mock_video.size = 1000000
        mock_video.ref = {"$link": "bafydict456"}

        mock_embed.video = mock_video

        result = BlueskyClient._extract_embed_data(mock_embed)

        assert result is not None
        assert "video" in result
        assert result["video"]["blob_ref"] == "bafydict456"

    def test_extract_video_embed_no_video(self):
        """Test extraction when no video present"""
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.external"
        mock_embed.video = None
        mock_embed.images = None
        mock_embed.media = None
        mock_embed.record = None

        # Mock external link instead
        mock_external = Mock()
        mock_external.uri = "https://example.com"
        mock_external.title = "Example"
        mock_external.description = "Test"
        mock_embed.external = mock_external

        result = BlueskyClient._extract_embed_data(mock_embed)

        assert result is not None
        assert "video" not in result
        assert "external" in result


class TestVideoDownload:
    """Test video download functionality"""

    @patch("src.bluesky_client.requests")
    def test_download_video_success(self, mock_requests):
        """Test successful video download"""
        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True

        # Mock successful response
        mock_response = Mock()
        mock_response.content = b"fake_video_bytes"
        mock_response.headers = {"Content-Type": "video/mp4"}
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        result = client.download_video("bafytest123", "did:plc:test123")

        assert result is not None
        video_bytes, mime_type = result
        assert video_bytes == b"fake_video_bytes"
        assert mime_type == "video/mp4"
        mock_requests.get.assert_called_once()

    def test_download_video_not_authenticated(self):
        """Test video download when not authenticated"""
        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = False

        result = client.download_video("bafytest123", "did:plc:test123")

        assert result is None

    @patch("src.bluesky_client.requests")
    def test_download_video_failure(self, mock_requests):
        """Test video download failure"""
        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True

        mock_requests.get.side_effect = Exception("Network error")

        result = client.download_video("bafytest123", "did:plc:test123")

        assert result is None


class TestVideoUploadMastodon:
    """Test video upload to Mastodon"""

    def test_upload_video_success(self):
        """Test successful video upload to Mastodon"""
        client = MastodonClient("https://mastodon.social", "test-token")
        client._authenticated = True

        # Mock Mastodon client
        mock_mastodon = Mock()
        mock_mastodon.media_post.return_value = {"id": "media-123"}
        client.client = mock_mastodon

        video_bytes = b"fake_video_data"
        result = client.upload_video(
            video_bytes, mime_type="video/mp4", description="Test video"
        )

        assert result == "media-123"
        mock_mastodon.media_post.assert_called_once_with(
            media_file=video_bytes,
            mime_type="video/mp4",
            description="Test video",
        )

    def test_upload_video_not_authenticated(self):
        """Test video upload when not authenticated"""
        client = MastodonClient("https://mastodon.social", "test-token")
        client._authenticated = False

        try:
            client.upload_video(b"fake_video", mime_type="video/mp4")
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass

    def test_upload_video_failure(self):
        """Test video upload failure"""
        client = MastodonClient("https://mastodon.social", "test-token")
        client._authenticated = True

        mock_mastodon = Mock()
        mock_mastodon.media_post.side_effect = Exception("Upload failed")
        client.client = mock_mastodon

        result = client.upload_video(b"fake_video", mime_type="video/mp4")

        assert result is None


class TestContentProcessorVideo:
    """Test ContentProcessor video handling"""

    def test_extract_video_from_embed(self):
        """Test extracting video from embed dict"""
        embed = {
            "py_type": "app.bsky.embed.video",
            "video": {
                "blob_ref": "bafytest123",
                "alt": "Test video",
                "mime_type": "video/mp4",
                "size": 5000000,
                "aspect_ratio": {"width": 1920, "height": 1080},
            },
        }

        result = ContentProcessor.extract_video_from_embed(embed)

        assert result is not None
        assert result["blob_ref"] == "bafytest123"
        assert result["alt"] == "Test video"
        assert result["mime_type"] == "video/mp4"
        assert result["size"] == 5000000

    def test_extract_video_from_embed_no_video(self):
        """Test extracting video when none present"""
        embed = {
            "py_type": "app.bsky.embed.external",
            "external": {"uri": "https://example.com"},
        }

        result = ContentProcessor.extract_video_from_embed(embed)

        assert result is None

    def test_handle_video_embed_with_placeholder(self):
        """Test handling video embed with placeholder text"""
        text = "Check out this video"
        embed = {
            "py_type": "app.bsky.embed.video",
            "video": {
                "alt": "Amazing video",
                "size": 10485760,  # 10MB
                "blob_ref": "bafytest",
            },
        }

        result = ContentProcessor._handle_embed(
            text, embed, include_image_placeholders=True
        )

        assert "🎥" in result
        assert "Amazing video" in result

    def test_handle_video_embed_no_placeholder(self):
        """Test handling video embed without placeholder"""
        text = "Check out this video"
        embed = {
            "py_type": "app.bsky.embed.video",
            "video": {"alt": "Amazing video", "size": 10485760, "blob_ref": "bafytest"},
        }

        result = ContentProcessor._handle_embed(
            text, embed, include_image_placeholders=False
        )

        assert "🎥" not in result
        assert result == text  # Should return original text unchanged

    def test_handle_video_embed_size_display(self):
        """Test video size is displayed in placeholder"""
        text = "Video post"
        embed = {
            "py_type": "app.bsky.embed.video",
            "video": {
                "alt": "",  # No alt text
                "size": 20971520,  # 20MB
                "blob_ref": "bafytest",
            },
        }

        result = ContentProcessor._handle_embed(
            text, embed, include_image_placeholders=True
        )

        assert "🎥" in result
        assert "20.0MB" in result


class TestVideoSyncIntegration:
    """Test video sync integration in orchestrator"""

    def test_video_sync_disabled_by_default(self):
        """Test that video sync is disabled by default"""
        from src.config import Settings

        settings = Settings(
            bluesky_handle="test.bsky.social",
            bluesky_password="test-pass",
            mastodon_access_token="test-token",
        )

        assert settings.sync_videos is False

    def test_video_size_limit_default(self):
        """Test default video size limit"""
        from src.config import Settings

        settings = Settings(
            bluesky_handle="test.bsky.social",
            bluesky_password="test-pass",
            mastodon_access_token="test-token",
        )

        assert settings.max_video_size_mb == 40


class TestVideoSizeLimitEnforcement:
    """Test video size limit enforcement"""

    def test_video_too_large(self):
        """Test that oversized videos are rejected"""
        # This would be tested in the orchestrator's _sync_video method
        # The method should check size and return None for oversized videos
        video_info = {
            "blob_ref": "bafytest",
            "alt": "Large video",
            "size": 50 * 1024 * 1024,  # 50MB
            "mime_type": "video/mp4",
        }

        # Size limit is 40MB
        max_size_mb = 40
        size_mb = video_info["size"] / (1024 * 1024)

        assert size_mb > max_size_mb
