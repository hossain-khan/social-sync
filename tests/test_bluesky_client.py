"""
Tests for Bluesky Client
"""
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.bluesky_client import BlueskyClient, BlueskyPost


class TestBlueskyClient:
    """Test suite for BlueskyClient class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = BlueskyClient("test.bsky.social", "test-password")

    @patch('src.bluesky_client.AtprotoClient')
    def test_init(self, mock_client_class):
        """Test client initialization"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")

        assert client.handle == "test.bsky.social"
        assert client.password == "test-password"
        assert client.client == mock_client
        assert client._authenticated is False

    @patch('src.bluesky_client.AtprotoClient')
    def test_authenticate_success(self, mock_client_class):
        """Test successful authentication"""
        mock_client = Mock()
        mock_profile = Mock()
        mock_profile.handle = "test.bsky.social"
        mock_profile.display_name = "Test User"
        mock_client.login.return_value = mock_profile
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        result = client.authenticate()

        assert result is True
        assert client._authenticated is True
        mock_client.login.assert_called_once_with("test.bsky.social", "test-password")

    @patch('src.bluesky_client.AtprotoClient')
    def test_authenticate_failure(self, mock_client_class):
        """Test authentication failure"""
        mock_client = Mock()
        mock_client.login.side_effect = Exception("Authentication failed")
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "invalid-password")
        result = client.authenticate()
        
        assert result is False
        assert client.session is None

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_user_did_authenticated(self, mock_client_class):
        """Test getting user DID when authenticated"""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.did = "did:plc:test123"
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        client.session = mock_session
        
        result = client.get_user_did()
        assert result == "did:plc:test123"

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_user_did_not_authenticated(self, mock_client_class):
        """Test getting user DID when not authenticated"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        client.session = None
        
        result = client.get_user_did()
        assert result is None

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_recent_posts_empty(self, mock_client_class):
        """Test getting recent posts when no posts exist"""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.handle = "test.bsky.social"
        
        # Mock empty feed response
        mock_response = Mock()
        mock_response.feed = []
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        client.session = mock_session
        
        result = client.get_recent_posts()
        
        assert result == []
        mock_client.get_author_feed.assert_called_once()

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_recent_posts_with_posts(self, mock_client_class):
        """Test getting recent posts with actual posts"""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.handle = "test.bsky.social"
        
        # Mock feed response with posts
        mock_post_record = Mock()
        mock_post_record.text = "Test post content"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = None
        mock_post_record.reply = None
        
        mock_feed_item = Mock()
        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = "at://did:plc:test123/app.bsky.feed.post/12345"
        mock_feed_item.post.cid = "test-cid"
        mock_feed_item.post.record = mock_post_record
        mock_feed_item.post.author = Mock()
        mock_feed_item.post.author.handle = "test.bsky.social"
        mock_feed_item.post.author.display_name = "Test User"
        
        mock_response = Mock()
        mock_response.feed = [mock_feed_item]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        client.session = mock_session
        
        result = client.get_recent_posts(limit=10)
        
        assert len(result) == 1
        post = result[0]
        assert isinstance(post, BlueskyPost)
        assert post.uri == "at://did:plc:test123/app.bsky.feed.post/12345"
        assert post.text == "Test post content"
        assert post.author_handle == "test.bsky.social"
        assert post.author_display_name == "Test User"

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_recent_posts_with_reply(self, mock_client_class):
        """Test getting recent posts including reply posts"""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.handle = "test.bsky.social"
        
        # Mock reply post record
        mock_reply = Mock()
        mock_reply.root = Mock()
        mock_reply.root.uri = "at://parent-post-uri"
        mock_reply.parent = Mock()
        mock_reply.parent.uri = "at://parent-post-uri"
        
        mock_post_record = Mock()
        mock_post_record.text = "This is a reply"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = None
        mock_post_record.reply = mock_reply
        
        mock_feed_item = Mock()
        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = "at://reply-post-uri"
        mock_feed_item.post.cid = "reply-cid"
        mock_feed_item.post.record = mock_post_record
        mock_feed_item.post.author = Mock()
        mock_feed_item.post.author.handle = "test.bsky.social"
        mock_feed_item.post.author.display_name = "Test User"
        
        mock_response = Mock()
        mock_response.feed = [mock_feed_item]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        client.session = mock_session
        
        result = client.get_recent_posts()
        
        assert len(result) == 1
        post = result[0]
        assert post.reply_to == "at://parent-post-uri"

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_recent_posts_with_since_date_filter(self, mock_client_class):
        """Test getting recent posts with since_date filtering"""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.handle = "test.bsky.social"
        
        # Mock posts with different dates
        def create_mock_post(uri, created_at):
            mock_post_record = Mock()
            mock_post_record.text = f"Post {uri}"
            mock_post_record.created_at = created_at
            mock_post_record.facets = []
            mock_post_record.embed = None
            mock_post_record.reply = None
            
            mock_feed_item = Mock()
            mock_feed_item.post = Mock()
            mock_feed_item.post.uri = uri
            mock_feed_item.post.cid = f"cid-{uri}"
            mock_feed_item.post.record = mock_post_record
            mock_feed_item.post.author = Mock()
            mock_feed_item.post.author.handle = "test.bsky.social"
            mock_feed_item.post.author.display_name = "Test User"
            return mock_feed_item
        
        old_post = create_mock_post("at://old-post", "2024-12-01T10:00:00.000Z")
        new_post = create_mock_post("at://new-post", "2025-01-15T10:00:00.000Z")
        
        mock_response = Mock()
        mock_response.feed = [old_post, new_post]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        client.session = mock_session
        
        # Filter posts since 2025-01-01
        since_date = datetime(2025, 1, 1)
        result = client.get_recent_posts(since_date=since_date)
        
        # Should only return the new post
        assert len(result) == 1
        assert result[0].uri == "at://new-post"

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_recent_posts_with_embed(self, mock_client_class):
        """Test getting posts with embed content"""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.handle = "test.bsky.social"
        
        # Mock embed data
        mock_embed = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": "https://example.com",
                "title": "Example Site",
                "description": "Test description"
            }
        }
        
        mock_post_record = Mock()
        mock_post_record.text = "Check this out"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = mock_embed
        mock_post_record.reply = None
        
        mock_feed_item = Mock()
        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = "at://post-with-embed"
        mock_feed_item.post.cid = "embed-cid"
        mock_feed_item.post.record = mock_post_record
        mock_feed_item.post.author = Mock()
        mock_feed_item.post.author.handle = "test.bsky.social"
        mock_feed_item.post.author.display_name = "Test User"
        
        mock_response = Mock()
        mock_response.feed = [mock_feed_item]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        client.session = mock_session
        
        result = client.get_recent_posts()
        
        assert len(result) == 1
        post = result[0]
        assert post.embed is not None
        assert post.embed["$type"] == "app.bsky.embed.external"

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_post_thread(self, mock_client_class):
        """Test getting post thread"""
        mock_client = Mock()
        mock_thread_response = Mock()
        mock_thread_response.thread = Mock()
        mock_client.get_post_thread.return_value = mock_thread_response
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        
        result = client.get_post_thread("at://test-post-uri")
        
        assert result == mock_thread_response.thread
        mock_client.get_post_thread.assert_called_once_with("at://test-post-uri")

    @patch('src.bluesky_client.AtprotoClient')
    def test_get_post_thread_error(self, mock_client_class):
        """Test getting post thread with error"""
        mock_client = Mock()
        mock_client.get_post_thread.side_effect = Exception("Thread not found")
        mock_client_class.return_value = mock_client
        
        client = BlueskyClient("test.bsky.social", "test-password")
        
        result = client.get_post_thread("at://invalid-uri")
        
        assert result is None

    @patch('src.bluesky_client.AtprotoClient')  
    @patch('bluesky_client.requests.get')
    def test_download_blob_success(self, mock_get, mock_client_class):
        """Test successful blob download"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = BlueskyClient("test.bsky.social", "test-password")
        
        result = client.download_blob("test-blob-ref", "did:plc:test123")
        
        assert result is not None
        content, mime_type = result
        assert content == b"fake_image_data"
        assert mime_type == "image/jpeg"

    @patch('src.bluesky_client.AtprotoClient')
    @patch('bluesky_client.requests.get')
    def test_download_blob_failure(self, mock_get, mock_client_class):
        """Test failed blob download"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_get.side_effect = Exception("Network error")
        
        client = BlueskyClient("test.bsky.social", "test-password")
        
        result = client.download_blob("test-blob-ref", "did:plc:test123")
        
        assert result is None

    def test_extract_facets_data_empty(self):
        """Test extracting facets data from empty facets"""
        result = BlueskyClient._extract_facets_data([])
        assert result == []

    def test_extract_facets_data_with_links(self):
        """Test extracting facets data with links"""
        facets = [
            {
                "index": {"byteStart": 0, "byteEnd": 10},
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": "https://example.com"
                    }
                ]
            }
        ]
        
        result = BlueskyClient._extract_facets_data(facets)
        
        assert len(result) == 1
        assert result[0]["index"]["byteStart"] == 0
        assert result[0]["features"][0]["uri"] == "https://example.com"

    def test_extract_embed_data_none(self):
        """Test extracting embed data from None"""
        result = BlueskyClient._extract_embed_data(None)
        assert result is None

    def test_extract_embed_data_external(self):
        """Test extracting external embed data"""
        embed = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": "https://example.com",
                "title": "Example"
            }
        }
        
        result = BlueskyClient._extract_embed_data(embed)
        
        assert result is not None
        assert result["$type"] == "app.bsky.embed.external"
        assert result["external"]["uri"] == "https://example.com"
