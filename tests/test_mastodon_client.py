from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.mastodon_client import MastodonClient, MastodonPost


@pytest.fixture
def mock_mastodon_library():
    """Fixture to patch the Mastodon library."""
    with patch("src.mastodon_client.Mastodon") as mock:
        yield mock


class TestMastodonClient:
    """Tests for the MastodonClient."""

    def test_init(self):
        """Test client initialization."""
        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        assert client.api_base_url == "https://mastodon.social"
        assert client.access_token == "test_token"
        assert client.client is None
        assert not client._authenticated

    def test_authenticate_success(self, mock_mastodon_library):
        """Test successful authentication."""
        mock_api = MagicMock()
        mock_api.me.return_value = {"username": "testuser"}
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        assert client.authenticate()
        assert client._authenticated
        mock_mastodon_library.assert_called_with(
            access_token="test_token", api_base_url="https://mastodon.social"
        )
        mock_api.me.assert_called_once()

    def test_authenticate_failure(self, mock_mastodon_library):
        """Test authentication failure."""
        mock_mastodon_library.side_effect = Exception("Auth error")
        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        assert not client.authenticate()
        assert not client._authenticated

    def test_post_status_not_authenticated(self):
        """Test posting status without authentication raises RuntimeError."""
        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        with pytest.raises(RuntimeError, match="Client not authenticated"):
            client.post_status("Hello world")

    def test_post_status_success(self, mock_mastodon_library):
        """Test successful status posting."""
        mock_api = MagicMock()
        mock_api.status_post.return_value = {
            "id": "123",
            "url": "https://mastodon.social/@testuser/123",
        }
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client.authenticate()  # Authenticate the client first

        status = client.post_status("Hello", in_reply_to_id="122", media_ids=["m1"])
        assert status is not None
        assert status["id"] == "123"
        mock_api.status_post.assert_called_with(
            status="Hello",
            in_reply_to_id="122",
            media_ids=["m1"],
            sensitive=False,
            spoiler_text=None,
            language=None,
        )

    def test_post_status_failure(self, mock_mastodon_library):
        """Test status posting failure."""
        mock_api = MagicMock()
        mock_api.status_post.side_effect = Exception("Post error")
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client.authenticate()

        status = client.post_status("Hello")
        assert status is None

    def test_upload_media_not_authenticated(self):
        """Test uploading media without authentication raises RuntimeError."""
        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        with pytest.raises(RuntimeError, match="Client not authenticated"):
            client.upload_media(b"some_media_bytes", "image/png")

    def test_upload_media_success(self, mock_mastodon_library):
        """Test successful media upload."""
        mock_api = MagicMock()
        mock_api.media_post.return_value = {"id": "m123"}
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client.authenticate()

        media_id = client.upload_media(b"image_data", "image/jpeg", "A test image")
        assert media_id == "m123"
        mock_api.media_post.assert_called_with(
            media_file=b"image_data", mime_type="image/jpeg", description="A test image"
        )

    def test_upload_media_failure(self, mock_mastodon_library):
        """Test media upload failure."""
        mock_api = MagicMock()
        mock_api.media_post.side_effect = Exception("Upload error")
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client.authenticate()

        media_id = client.upload_media(b"image_data")
        assert media_id is None

    def test_get_recent_posts_not_authenticated(self):
        """Test getting posts without authentication raises RuntimeError."""
        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        with pytest.raises(RuntimeError, match="Client not authenticated"):
            client.get_recent_posts()

    def test_get_recent_posts_success(self, mock_mastodon_library):
        """Test successfully getting recent posts."""
        mock_api = MagicMock()
        mock_api.me.return_value = {"id": "user1"}
        mock_api.account_statuses.return_value = [
            {
                "id": "p1",
                "content": "Post 1",
                "created_at": datetime.now(),
                "url": "url1",
                "in_reply_to_id": None,
                "media_attachments": [],
            },
            {
                "id": "p2",
                "content": "Reply to p1",
                "created_at": datetime.now(),
                "url": "url2",
                "in_reply_to_id": "p1",
                "media_attachments": [{"id": "m1"}],
            },
        ]
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client.authenticate()

        posts = client.get_recent_posts(limit=5)
        assert len(posts) == 2
        assert isinstance(posts[0], MastodonPost)
        assert posts[0].id == "p1"
        assert posts[1].in_reply_to_id == "p1"
        assert posts[1].media_attachments[0]["id"] == "m1"
        mock_api.account_statuses.assert_called_with(id="user1", limit=5)

    def test_get_recent_posts_failure(self, mock_mastodon_library):
        """Test failure when getting recent posts."""
        mock_api = MagicMock()
        mock_api.me.return_value = {"id": "user1"}
        mock_api.account_statuses.side_effect = Exception("Fetch error")
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client.authenticate()

        posts = client.get_recent_posts()
        assert posts == []

    @patch("src.mastodon_client.Mastodon")
    def test_post_status_with_content_warning(self, mock_mastodon_library):
        """Test posting a status with content warning"""
        mock_api = MagicMock()
        mock_api.status_post.return_value = {
            "id": "post123",
            "content": "Test post",
            "sensitive": True,
            "spoiler_text": "NSFW - Adult Content",
        }
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client._authenticated = True
        client.client = mock_api

        result = client.post_status(
            "Test post",
            sensitive=True,
            spoiler_text="NSFW - Adult Content",
        )

        assert result is not None
        assert result["id"] == "post123"
        assert result["sensitive"] is True
        assert result["spoiler_text"] == "NSFW - Adult Content"
        mock_api.status_post.assert_called_once_with(
            status="Test post",
            in_reply_to_id=None,
            media_ids=None,
            sensitive=True,
            spoiler_text="NSFW - Adult Content",
            language=None,
        )

    @patch("src.mastodon_client.Mastodon")
    def test_post_status_without_content_warning(self, mock_mastodon_library):
        """Test posting a status without content warning"""
        mock_api = MagicMock()
        mock_api.status_post.return_value = {
            "id": "post123",
            "content": "Test post",
            "sensitive": False,
            "spoiler_text": None,
        }
        mock_mastodon_library.return_value = mock_api

        client = MastodonClient(
            api_base_url="https://mastodon.social", access_token="test_token"
        )
        client._authenticated = True
        client.client = mock_api

        result = client.post_status(
            "Test post",
            sensitive=False,
            spoiler_text=None,
        )

        assert result is not None
        assert result["id"] == "post123"
        assert result["sensitive"] is False
        assert result["spoiler_text"] is None
        mock_api.status_post.assert_called_once_with(
            status="Test post",
            in_reply_to_id=None,
            media_ids=None,
            sensitive=False,
            spoiler_text=None,
            language=None,
        )
