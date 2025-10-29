"""
Additional tests for Mastodon Client module to improve coverage
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.mastodon_client import MastodonClient, MastodonPost


class TestMastodonClientEdgeCases:
    """Additional tests for MastodonClient edge cases to improve coverage"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = MastodonClient("https://mastodon.social", "test-token")

    def test_authentication_failure_scenarios(self):
        """Test various authentication failure scenarios"""
        with patch("src.mastodon_client.Mastodon") as mock_mastodon_class:
            # Test Mastodon client creation failure
            mock_mastodon_class.side_effect = Exception("Failed to create client")

            result = self.client.authenticate()
            assert result is False
            assert self.client._authenticated is False

    def test_authentication_credential_verification_failure(self):
        """Test authentication failure during credential verification"""
        with patch("src.mastodon_client.Mastodon") as mock_mastodon_class:
            mock_mastodon_instance = Mock()
            mock_mastodon_instance.me.side_effect = Exception("Invalid credentials")
            mock_mastodon_class.return_value = mock_mastodon_instance

            result = self.client.authenticate()
            assert result is False
            assert self.client._authenticated is False

    def test_authentication_success(self):
        """Test successful authentication"""
        with patch("src.mastodon_client.Mastodon") as mock_mastodon_class:
            mock_mastodon_instance = Mock()
            mock_account = {"username": "testuser", "id": "123"}
            mock_mastodon_instance.me.return_value = mock_account
            mock_mastodon_class.return_value = mock_mastodon_instance

            result = self.client.authenticate()
            assert result is True
            assert self.client._authenticated is True
            assert self.client.client == mock_mastodon_instance

    def test_authentication_none_client_response(self):
        """Test authentication when Mastodon client creation returns None"""
        with patch("src.mastodon_client.Mastodon") as mock_mastodon_class:
            mock_mastodon_class.return_value = None

            result = self.client.authenticate()
            assert result is False
            assert self.client._authenticated is False

    def test_post_status_not_authenticated(self):
        """Test post_status when not authenticated"""
        with pytest.raises(RuntimeError) as exc_info:
            self.client.post_status("Test status")

        assert "not authenticated" in str(exc_info.value)

    def test_post_status_no_client(self):
        """Test post_status when client is None"""
        self.client._authenticated = True
        self.client.client = None

        with pytest.raises(RuntimeError) as exc_info:
            self.client.post_status("Test status")

        assert "not authenticated" in str(exc_info.value)

    def test_post_status_success(self):
        """Test successful status posting"""
        mock_client = Mock()
        mock_status = {
            "id": "123456789",
            "url": "https://mastodon.social/@user/123456789",
        }
        mock_client.status_post.return_value = mock_status

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.post_status("Test status")

        assert result == mock_status
        mock_client.status_post.assert_called_once_with(
            status="Test status",
            in_reply_to_id=None,
            media_ids=None,
            sensitive=False,
            spoiler_text=None,
        )

    def test_post_status_with_reply_and_media(self):
        """Test status posting with reply and media"""
        mock_client = Mock()
        mock_status = {"id": "123456789"}
        mock_client.status_post.return_value = mock_status

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.post_status(
            "Test reply", in_reply_to_id="987654321", media_ids=["media1", "media2"]
        )

        assert result == mock_status
        mock_client.status_post.assert_called_once_with(
            status="Test reply",
            in_reply_to_id="987654321",
            media_ids=["media1", "media2"],
            sensitive=False,
            spoiler_text=None,
        )

    def test_post_status_api_exception(self):
        """Test post_status when API call fails"""
        mock_client = Mock()
        mock_client.status_post.side_effect = Exception("API error")

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.post_status("Test status")
        assert result is None

    def test_post_status_non_dict_response(self):
        """Test post_status when API returns non-dict response"""
        mock_client = Mock()
        mock_client.status_post.return_value = "not a dict"

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.post_status("Test status")
        assert result is None

    def test_upload_media_not_authenticated(self):
        """Test upload_media when not authenticated"""
        with pytest.raises(RuntimeError) as exc_info:
            self.client.upload_media(b"fake image data")

        assert "not authenticated" in str(exc_info.value)

    def test_upload_media_no_client(self):
        """Test upload_media when client is None"""
        self.client._authenticated = True
        self.client.client = None

        with pytest.raises(RuntimeError) as exc_info:
            self.client.upload_media(b"fake image data")

        assert "not authenticated" in str(exc_info.value)

    def test_upload_media_success(self):
        """Test successful media upload"""
        mock_client = Mock()
        mock_media = {
            "id": "media123",
            "url": "https://files.mastodon.social/media/123",
        }
        mock_client.media_post.return_value = mock_media

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.upload_media(
            b"fake image data", mime_type="image/jpeg", description="Test image"
        )

        assert result == "media123"
        mock_client.media_post.assert_called_once_with(
            media_file=b"fake image data",
            mime_type="image/jpeg",
            description="Test image",
        )

    def test_upload_media_api_exception(self):
        """Test upload_media when API call fails"""
        mock_client = Mock()
        mock_client.media_post.side_effect = Exception("Upload failed")

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.upload_media(b"fake image data")
        assert result is None

    def test_upload_media_non_dict_response(self):
        """Test upload_media when API returns non-dict response"""
        mock_client = Mock()
        mock_client.media_post.return_value = "not a dict"

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.upload_media(b"fake image data")
        assert result is None

    def test_upload_media_missing_id(self):
        """Test upload_media when response missing ID"""
        mock_client = Mock()
        mock_media = {"url": "https://files.mastodon.social/media/123"}  # Missing 'id'
        mock_client.media_post.return_value = mock_media

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.upload_media(b"fake image data")
        assert result is None

    def test_get_recent_posts_not_authenticated(self):
        """Test get_recent_posts when not authenticated"""
        with pytest.raises(RuntimeError) as exc_info:
            self.client.get_recent_posts(limit=10)

        assert "not authenticated" in str(exc_info.value)

    def test_get_recent_posts_no_client(self):
        """Test get_recent_posts when client is None"""
        self.client._authenticated = True
        self.client.client = None

        with pytest.raises(RuntimeError) as exc_info:
            self.client.get_recent_posts(limit=10)

        assert "not authenticated" in str(exc_info.value)

    def test_get_recent_posts_success(self):
        """Test successful get_recent_posts"""
        mock_client = Mock()
        mock_account = {"id": "user123"}
        mock_client.me.return_value = mock_account

        mock_statuses = [
            {
                "id": "status1",
                "content": "First post",
                "created_at": datetime.now(),
                "url": "https://mastodon.social/@user/status1",
                "in_reply_to_id": None,
                "media_attachments": [],
            },
            {
                "id": "status2",
                "content": "Second post",
                "created_at": datetime.now(),
                "url": "https://mastodon.social/@user/status2",
                "in_reply_to_id": None,
                "media_attachments": [],
            },
        ]
        mock_client.account_statuses.return_value = mock_statuses

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.get_recent_posts(limit=10)

        assert len(result) == 2
        assert all(isinstance(post, MastodonPost) for post in result)
        assert result[0].id == "status1"
        assert result[1].id == "status2"

        mock_client.account_statuses.assert_called_once_with(id="user123", limit=10)

    def test_get_recent_posts_api_exception(self):
        """Test get_recent_posts when API call fails"""
        mock_client = Mock()
        mock_client.me.side_effect = Exception("API error")

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.get_recent_posts(limit=10)
        assert result == []

    def test_get_recent_posts_account_statuses_exception(self):
        """Test get_recent_posts when account_statuses call fails"""
        mock_client = Mock()
        mock_account = {"id": "user123"}
        mock_client.me.return_value = mock_account
        mock_client.account_statuses.side_effect = Exception("API error")

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.get_recent_posts(limit=10)
        assert result == []

    def test_get_recent_posts_with_limit(self):
        """Test get_recent_posts with custom limit parameter"""
        mock_client = Mock()
        mock_account = {"id": "user123"}
        mock_client.me.return_value = mock_account
        mock_client.account_statuses.return_value = []

        self.client._authenticated = True
        self.client.client = mock_client

        result = self.client.get_recent_posts(limit=5)

        mock_client.account_statuses.assert_called_once_with(id="user123", limit=5)

    def test_mastodon_post_creation_with_all_fields(self):
        """Test MastodonPost dataclass with all fields"""
        now = datetime.now()

        post = MastodonPost(
            id="123456789",
            content="Test post content",
            created_at=now,
            url="https://mastodon.social/@user/123456789",
            in_reply_to_id="987654321",
            media_attachments=[
                {
                    "id": "media1",
                    "type": "image",
                    "url": "https://example.com/image1.jpg",
                },
                {
                    "id": "media2",
                    "type": "image",
                    "url": "https://example.com/image2.jpg",
                },
            ],
        )

        assert post.id == "123456789"
        assert post.content == "Test post content"
        assert post.created_at == now
        assert post.url == "https://mastodon.social/@user/123456789"
        assert post.in_reply_to_id == "987654321"
        assert len(post.media_attachments) == 2

    def test_mastodon_post_creation_minimal(self):
        """Test MastodonPost dataclass with minimal required fields"""
        now = datetime.now()

        post = MastodonPost(
            id="123456789",
            content="Test post content",
            created_at=now,
            url="https://mastodon.social/@user/123456789",
        )

        assert post.id == "123456789"
        assert post.content == "Test post content"
        assert post.created_at == now
        assert post.url == "https://mastodon.social/@user/123456789"
        assert post.in_reply_to_id is None
        assert post.media_attachments is None

    def test_different_base_urls(self):
        """Test MastodonClient with different base URLs"""
        test_urls = [
            "https://mastodon.social",
            "https://fosstodon.org",
            "https://mas.to",
            "https://custom-instance.com",
        ]

        for url in test_urls:
            client = MastodonClient(url, "test-token")
            assert client.api_base_url == url
            assert client.access_token == "test-token"
            assert client._authenticated is False

    def test_empty_credentials(self):
        """Test MastodonClient with empty credentials"""
        client = MastodonClient("", "")
        assert client.api_base_url == ""
        assert client.access_token == ""
        assert client._authenticated is False

    def test_client_initialization_edge_cases(self):
        """Test client initialization with various edge cases"""
        # Test with None values (might cause issues in real usage)
        try:
            client = MastodonClient(None, None)
            assert client.api_base_url is None
            assert client.access_token is None
        except TypeError:
            # This might be acceptable behavior
            pass

        # Test with very long URLs and tokens
        long_url = "https://" + "a" * 1000 + ".com"
        long_token = "token" * 1000

        client = MastodonClient(long_url, long_token)
        assert client.api_base_url == long_url
        assert client.access_token == long_token

    def test_media_upload_with_different_mime_types(self):
        """Test media upload with different MIME types"""
        mock_client = Mock()
        mock_media = {"id": "media123"}
        mock_client.media_post.return_value = mock_media

        self.client._authenticated = True
        self.client.client = mock_client

        mime_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "video/mp4",
            "audio/mpeg",
            None,  # No MIME type specified
        ]

        for mime_type in mime_types:
            result = self.client.upload_media(b"fake media data", mime_type=mime_type)
            assert result == "media123"

    def test_status_posting_character_limits(self):
        """Test status posting with various content lengths"""
        mock_client = Mock()
        mock_status = {"id": "123"}
        mock_client.status_post.return_value = mock_status

        self.client._authenticated = True
        self.client.client = mock_client

        # Test various content lengths
        test_contents = [
            "",  # Empty status
            "Short",  # Very short
            "A" * 500,  # Maximum typical length
            "A" * 1000,  # Very long (might be truncated by Mastodon)
            "Unicode test: 🦋🌟✨",  # Unicode characters
            "Newlines\nand\ntabs\there",  # Special characters
        ]

        for content in test_contents:
            result = self.client.post_status(content)
            assert result == mock_status
