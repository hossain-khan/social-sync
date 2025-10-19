"""
Tests for Bluesky Client
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

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

    @patch("src.bluesky_client.AtprotoClient")
    def test_init(self, mock_client_class):
        """Test client initialization"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")

        assert client.handle == "test.bsky.social"
        assert client.password == "test-password"
        assert client.client == mock_client
        assert client._authenticated is False

    @patch("src.bluesky_client.AtprotoClient")
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

    @patch("src.bluesky_client.AtprotoClient")
    def test_authenticate_failure(self, mock_client_class):
        """Test authentication failure"""
        mock_client = Mock()
        mock_client.login.side_effect = Exception("Authentication failed")
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "invalid-password")
        result = client.authenticate()

        assert result is False
        assert client._authenticated is False

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_user_did_authenticated(self, mock_client_class):
        """Test getting user DID when authenticated"""
        mock_client = Mock()
        mock_me = Mock()
        mock_me.did = "did:plc:test123"
        mock_client.me = mock_me
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True  # Set authenticated directly for this test

        result = client.get_user_did()
        assert result == "did:plc:test123"

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_user_did_not_authenticated(self, mock_client_class):
        """Test getting user DID when not authenticated"""
        mock_client = Mock()
        # Make authentication fail
        mock_client.login.side_effect = Exception("Not authenticated")
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        # Client starts as not authenticated

        result = client.get_user_did()
        assert result is None

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_empty(self, mock_client_class):
        """Test getting recent posts when no posts exist"""
        mock_client = Mock()

        # Mock empty feed response
        mock_response = Mock()
        mock_response.feed = []
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True  # Set authenticated directly for this test

        result = client.get_recent_posts()

        assert result.posts == []
        assert result.total_retrieved == 0
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0
        mock_client.get_author_feed.assert_called_once()

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_with_posts(self, mock_client_class):
        """Test getting recent posts with actual posts"""
        mock_client = Mock()

        # Mock feed response with posts
        mock_post_record = Mock()
        mock_post_record.text = "Test post content"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = None
        mock_post_record.reply = None

        mock_feed_item = Mock()
        # Ensure no 'reason' attribute (no repost)
        if hasattr(mock_feed_item, "reason"):
            delattr(mock_feed_item, "reason")

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
        client._authenticated = True  # Set authenticated directly for this test

        result = client.get_recent_posts(limit=10)

        assert len(result.posts) == 1
        assert result.total_retrieved == 1
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0

        post = result.posts[0]
        assert isinstance(post, BlueskyPost)
        assert post.uri == "at://did:plc:test123/app.bsky.feed.post/12345"
        assert post.text == "Test post content"
        assert post.author_handle == "test.bsky.social"
        assert post.author_display_name == "Test User"

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_with_reply(self, mock_client_class):
        """Test that reply posts to others' posts are filtered out"""
        mock_client = Mock()
        mock_me = Mock()
        mock_me.did = "did:plc:test123"
        mock_client.me = mock_me

        # Mock reply post record - reply to someone else's post
        mock_reply = Mock()
        mock_reply.root = Mock()
        # Root belongs to someone else
        mock_reply.root.uri = "at://did:plc:otheruser456/app.bsky.feed.post/their-post"
        mock_reply.parent = Mock()
        mock_reply.parent.uri = "at://did:plc:otheruser456/app.bsky.feed.post/their-post"

        mock_post_record = Mock()
        mock_post_record.text = "This is a reply"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = None
        mock_post_record.reply = (
            mock_reply  # This should cause the post to be filtered out
        )

        mock_feed_item = Mock()
        # Ensure no 'reason' attribute (no repost)
        if hasattr(mock_feed_item, "reason"):
            delattr(mock_feed_item, "reason")

        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = "at://did:plc:test123/app.bsky.feed.post/reply-post"
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
        client._authenticated = True  # Set authenticated directly for this test

        result = client.get_recent_posts()

        # Reply posts to others should be filtered out
        assert len(result.posts) == 0
        assert result.total_retrieved == 1  # One post was retrieved from API
        assert result.filtered_replies == 1  # One reply was filtered out
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_with_self_reply_to_own_post(self, mock_client_class):
        """Test that self-replies to own posts are included"""
        mock_client = Mock()
        mock_me = Mock()
        mock_me.did = "did:plc:test123"
        mock_client.me = mock_me

        # Mock self-reply: reply to own post
        mock_reply = Mock()
        mock_reply.root = Mock()
        mock_reply.root.uri = "at://did:plc:test123/app.bsky.feed.post/original-post"
        mock_reply.parent = Mock()
        mock_reply.parent.uri = "at://did:plc:test123/app.bsky.feed.post/original-post"

        mock_post_record = Mock()
        mock_post_record.text = "This is a self-reply"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = None
        mock_post_record.reply = mock_reply

        mock_feed_item = Mock()
        if hasattr(mock_feed_item, "reason"):
            delattr(mock_feed_item, "reason")

        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = "at://did:plc:test123/app.bsky.feed.post/self-reply"
        mock_feed_item.post.cid = "self-reply-cid"
        mock_feed_item.post.record = mock_post_record
        mock_feed_item.post.author = Mock()
        mock_feed_item.post.author.handle = "test.bsky.social"
        mock_feed_item.post.author.display_name = "Test User"

        mock_response = Mock()
        mock_response.feed = [mock_feed_item]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True

        result = client.get_recent_posts()

        # Self-replies should be included
        assert len(result.posts) == 1
        assert result.total_retrieved == 1
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0
        assert result.posts[0].text == "This is a self-reply"

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_with_nested_reply_in_others_thread(self, mock_client_class):
        """Test that nested replies in threads started by others are filtered out
        
        This tests the bug fix: A reply to a self-reply that is itself part of
        someone else's thread should be filtered out.
        
        Thread structure:
        1. Someone else's post (root)
        2. User's reply to that post (would be filtered, not shown here)
        3. User's reply to their own reply (should be filtered - this is the bug)
        """
        mock_client = Mock()
        mock_me = Mock()
        mock_me.did = "did:plc:test123"
        mock_client.me = mock_me

        # Mock nested reply: reply to own reply, but root is someone else's post
        mock_reply = Mock()
        mock_reply.root = Mock()
        # Root is someone else's post
        mock_reply.root.uri = "at://did:plc:otheruser456/app.bsky.feed.post/their-post"
        mock_reply.parent = Mock()
        # Parent is user's own reply
        mock_reply.parent.uri = "at://did:plc:test123/app.bsky.feed.post/users-reply"

        mock_post_record = Mock()
        mock_post_record.text = "Reply to my reply in someone else's thread"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = None
        mock_post_record.reply = mock_reply

        mock_feed_item = Mock()
        if hasattr(mock_feed_item, "reason"):
            delattr(mock_feed_item, "reason")

        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = "at://did:plc:test123/app.bsky.feed.post/nested-reply"
        mock_feed_item.post.cid = "nested-reply-cid"
        mock_feed_item.post.record = mock_post_record
        mock_feed_item.post.author = Mock()
        mock_feed_item.post.author.handle = "test.bsky.social"
        mock_feed_item.post.author.display_name = "Test User"

        mock_response = Mock()
        mock_response.feed = [mock_feed_item]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True

        result = client.get_recent_posts()

        # Nested reply in someone else's thread should be filtered out
        assert len(result.posts) == 0
        assert result.total_retrieved == 1
        assert result.filtered_replies == 1
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_with_deep_nested_self_replies(self, mock_client_class):
        """Test that deeply nested self-replies in own threads are included
        
        Thread structure:
        1. User's original post (root)
        2. User's reply to their own post
        3. User's reply to their reply (deeply nested)
        """
        mock_client = Mock()
        mock_me = Mock()
        mock_me.did = "did:plc:test123"
        mock_client.me = mock_me

        # Mock deeply nested self-reply
        mock_reply = Mock()
        mock_reply.root = Mock()
        # Root is user's own post
        mock_reply.root.uri = "at://did:plc:test123/app.bsky.feed.post/original-post"
        mock_reply.parent = Mock()
        # Parent is also user's own reply
        mock_reply.parent.uri = "at://did:plc:test123/app.bsky.feed.post/first-reply"

        mock_post_record = Mock()
        mock_post_record.text = "Deep nested reply in my own thread"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = None
        mock_post_record.reply = mock_reply

        mock_feed_item = Mock()
        if hasattr(mock_feed_item, "reason"):
            delattr(mock_feed_item, "reason")

        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = (
            "at://did:plc:test123/app.bsky.feed.post/deep-nested-reply"
        )
        mock_feed_item.post.cid = "deep-nested-cid"
        mock_feed_item.post.record = mock_post_record
        mock_feed_item.post.author = Mock()
        mock_feed_item.post.author.handle = "test.bsky.social"
        mock_feed_item.post.author.display_name = "Test User"

        mock_response = Mock()
        mock_response.feed = [mock_feed_item]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True

        result = client.get_recent_posts()

        # Deep nested self-replies in own thread should be included
        assert len(result.posts) == 1
        assert result.total_retrieved == 1
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0
        assert result.posts[0].text == "Deep nested reply in my own thread"

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_with_since_date_filter(self, mock_client_class):
        """Test that posts are filtered by since_date"""
        mock_client = Mock()
        mock_session = Mock()
        mock_session.handle = "test.bsky.social"

        # Old post (should be filtered out)
        mock_old_post_record = Mock()
        mock_old_post_record.text = "Old post"
        mock_old_post_record.created_at = "2024-12-01T10:00:00.000Z"
        mock_old_post_record.facets = []
        mock_old_post_record.embed = None
        mock_old_post_record.reply = None

        mock_old_feed_item = Mock()
        # Ensure no 'reason' attribute (no repost)
        if hasattr(mock_old_feed_item, "reason"):
            delattr(mock_old_feed_item, "reason")

        mock_old_feed_item.post = Mock()
        mock_old_feed_item.post.uri = "at://old-post-uri"
        mock_old_feed_item.post.cid = "old-cid"
        mock_old_feed_item.post.record = mock_old_post_record
        mock_old_feed_item.post.author = Mock()
        mock_old_feed_item.post.author.handle = "test.bsky.social"
        mock_old_feed_item.post.author.display_name = "Test User"

        # New post (should be included)
        mock_new_post_record = Mock()
        mock_new_post_record.text = "New post"
        mock_new_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_new_post_record.facets = []
        mock_new_post_record.embed = None
        mock_new_post_record.reply = None

        mock_new_feed_item = Mock()
        # Ensure no 'reason' attribute (no repost)
        if hasattr(mock_new_feed_item, "reason"):
            delattr(mock_new_feed_item, "reason")

        mock_new_feed_item.post = Mock()
        mock_new_feed_item.post.uri = "at://new-post-uri"
        mock_new_feed_item.post.cid = "new-cid"
        mock_new_feed_item.post.record = mock_new_post_record
        mock_new_feed_item.post.author = Mock()
        mock_new_feed_item.post.author.handle = "test.bsky.social"
        mock_new_feed_item.post.author.display_name = "Test User"

        mock_response = Mock()
        mock_response.feed = [mock_old_feed_item, mock_new_feed_item]
        mock_client.get_author_feed.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True  # Set authenticated directly for this test

        since_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        result = client.get_recent_posts(since_date=since_date)

        assert len(result.posts) == 1
        assert result.posts[0].text == "New post"
        assert result.total_retrieved == 2  # Two posts retrieved
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 1  # One filtered by date

    @patch("src.bluesky_client.AtprotoClient")
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
                "description": "Test description",
            },
        }

        mock_post_record = Mock()
        mock_post_record.text = "Check this out"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.embed = mock_embed
        mock_post_record.reply = None

        mock_feed_item = Mock()
        # Ensure no 'reason' attribute (no repost)
        if hasattr(mock_feed_item, "reason"):
            delattr(mock_feed_item, "reason")

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
        client._authenticated = True  # Set authenticated directly for this test

        result = client.get_recent_posts()

        assert len(result.posts) == 1
        assert result.total_retrieved == 1
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0

        post = result.posts[0]
        assert post.embed is not None
        assert post.embed["py_type"] == "dict"

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_post_thread(self, mock_client_class):
        """Test getting post thread"""
        mock_client = Mock()
        mock_thread_response = Mock()
        # Make thread a dict to match the implementation expectation
        mock_thread_response.thread = {"post": {"uri": "at://test-post-uri"}}
        mock_client.get_post_thread.return_value = mock_thread_response
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")

        result = client.get_post_thread("at://test-post-uri")

        assert result == {"post": {"uri": "at://test-post-uri"}}
        mock_client.get_post_thread.assert_called_once_with(uri="at://test-post-uri")

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_post_thread_error(self, mock_client_class):
        """Test getting post thread with error"""
        mock_client = Mock()
        mock_client.get_post_thread.side_effect = Exception("Thread not found")
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")

        result = client.get_post_thread("at://invalid-uri")

        assert result is None

    @patch("src.bluesky_client.AtprotoClient")
    @patch("src.bluesky_client.requests.get")
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
        client._authenticated = True  # Set authenticated for blob download

        result = client.download_blob("test-blob-ref", "did:plc:test123")

        assert result is not None
        content, mime_type = result
        assert content == b"fake_image_data"
        assert mime_type == "image/jpeg"

    @patch("src.bluesky_client.AtprotoClient")
    @patch("src.bluesky_client.requests.get")
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
        # Create Mock objects that behave like AT Protocol facet objects
        mock_index = Mock()
        mock_index.byte_start = 0
        mock_index.byte_end = 10

        mock_feature = Mock()
        mock_feature.uri = "https://example.com"

        mock_facet = Mock()
        mock_facet.index = mock_index
        mock_facet.features = [mock_feature]

        facets = [mock_facet]

        result = BlueskyClient._extract_facets_data(facets)

        assert len(result) == 1
        assert result[0]["index"]["byteStart"] == 0
        assert result[0]["index"]["byteEnd"] == 10
        assert result[0]["features"][0]["uri"] == "https://example.com"

    def test_extract_embed_data_none(self):
        """Test extracting embed data from None"""
        result = BlueskyClient._extract_embed_data(None)
        assert result == {"py_type": "NoneType"}

    def test_extract_embed_data_external(self):
        """Test extracting external embed data"""
        # Create Mock objects that behave like AT Protocol embed objects
        mock_external = Mock()
        mock_external.uri = "https://example.com"
        mock_external.title = "Example"
        mock_external.description = "Test description"

        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.external"
        mock_embed.external = mock_external
        # Ensure images attribute doesn't exist to avoid iteration issues
        if hasattr(mock_embed, "images"):
            delattr(mock_embed, "images")
        # Ensure record attribute doesn't exist to avoid issues
        if hasattr(mock_embed, "record"):
            delattr(mock_embed, "record")

        result = BlueskyClient._extract_embed_data(mock_embed)

        assert result is not None
        assert result["py_type"] == "app.bsky.embed.external"
        assert result["external"]["uri"] == "https://example.com"
        assert result["external"]["title"] == "Example"

    def test_extract_embed_data_images_with_blob_reference(self):
        """Test extracting image embed data with blob reference - fix for image attachment bug"""
        # Create Mock objects that simulate AT Protocol image embed with blob reference
        mock_blob_ref = Mock()
        mock_blob_ref.link = (
            "bafkreihitajnhlutyalbqxutmfifkjxxrdqgl5basih3i7z2rjnmwpo4ya"
        )

        mock_image_blob = Mock()
        mock_image_blob.mime_type = "image/jpeg"
        mock_image_blob.size = 187302
        mock_image_blob.ref = mock_blob_ref

        mock_aspect_ratio = Mock()
        mock_aspect_ratio.height = 414
        mock_aspect_ratio.width = 1748
        mock_aspect_ratio.py_type = "app.bsky.embed.defs#aspectRatio"

        mock_image = Mock()
        mock_image.alt = ""
        mock_image.aspect_ratio = mock_aspect_ratio
        mock_image.image = mock_image_blob

        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.images"
        mock_embed.images = [mock_image]
        # Ensure other attributes don't exist
        if hasattr(mock_embed, "external"):
            delattr(mock_embed, "external")
        if hasattr(mock_embed, "record"):
            delattr(mock_embed, "record")

        result = BlueskyClient._extract_embed_data(mock_embed)

        # Verify the result contains proper blob reference
        assert result is not None
        assert result["py_type"] == "app.bsky.embed.images"
        assert "images" in result
        assert len(result["images"]) == 1

        image_data = result["images"][0]
        assert image_data["alt"] == ""
        assert image_data["aspect_ratio"] == mock_aspect_ratio
        assert "image" in image_data

        blob_data = image_data["image"]
        assert blob_data["mime_type"] == "image/jpeg"
        assert blob_data["size"] == 187302
        # This is the key fix - blob reference should be extracted
        assert "ref" in blob_data
        assert (
            blob_data["ref"]["$link"]
            == "bafkreihitajnhlutyalbqxutmfifkjxxrdqgl5basih3i7z2rjnmwpo4ya"
        )

    def test_extract_embed_data_multiple_images_with_blob_references(self):
        """Test extracting multiple image embed data with blob references"""
        # Create Mock objects for first image
        mock_blob_ref1 = Mock()
        mock_blob_ref1.link = (
            "bafkreihitajnhlutyalbqxutmfifkjxxrdqgl5basih3i7z2rjnmwpo4ya"
        )

        mock_image_blob1 = Mock()
        mock_image_blob1.mime_type = "image/jpeg"
        mock_image_blob1.size = 187302
        mock_image_blob1.ref = mock_blob_ref1

        mock_aspect_ratio1 = Mock()
        mock_aspect_ratio1.height = 414
        mock_aspect_ratio1.width = 1748

        mock_image1 = Mock()
        mock_image1.alt = "First image"
        mock_image1.aspect_ratio = mock_aspect_ratio1
        mock_image1.image = mock_image_blob1

        # Create Mock objects for second image
        mock_blob_ref2 = Mock()
        mock_blob_ref2.link = (
            "bafkreiabcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnop"
        )

        mock_image_blob2 = Mock()
        mock_image_blob2.mime_type = "image/png"
        mock_image_blob2.size = 245678
        mock_image_blob2.ref = mock_blob_ref2

        mock_aspect_ratio2 = Mock()
        mock_aspect_ratio2.height = 800
        mock_aspect_ratio2.width = 600

        mock_image2 = Mock()
        mock_image2.alt = "Second image"
        mock_image2.aspect_ratio = mock_aspect_ratio2
        mock_image2.image = mock_image_blob2

        # Create embed with multiple images
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.images"
        mock_embed.images = [mock_image1, mock_image2]
        if hasattr(mock_embed, "external"):
            delattr(mock_embed, "external")
        if hasattr(mock_embed, "record"):
            delattr(mock_embed, "record")

        result = BlueskyClient._extract_embed_data(mock_embed)

        # Verify the result contains both images with proper blob references
        assert result is not None
        assert result["py_type"] == "app.bsky.embed.images"
        assert "images" in result
        assert len(result["images"]) == 2

        # Verify first image
        image1_data = result["images"][0]
        assert image1_data["alt"] == "First image"
        assert image1_data["aspect_ratio"] == mock_aspect_ratio1
        assert "image" in image1_data

        blob1_data = image1_data["image"]
        assert blob1_data["mime_type"] == "image/jpeg"
        assert blob1_data["size"] == 187302
        assert "ref" in blob1_data
        assert (
            blob1_data["ref"]["$link"]
            == "bafkreihitajnhlutyalbqxutmfifkjxxrdqgl5basih3i7z2rjnmwpo4ya"
        )

        # Verify second image
        image2_data = result["images"][1]
        assert image2_data["alt"] == "Second image"
        assert image2_data["aspect_ratio"] == mock_aspect_ratio2
        assert "image" in image2_data

        blob2_data = image2_data["image"]
        assert blob2_data["mime_type"] == "image/png"
        assert blob2_data["size"] == 245678
        assert "ref" in blob2_data
        assert (
            blob2_data["ref"]["$link"]
            == "bafkreiabcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnop"
        )

    @patch("src.bluesky_client.AtprotoClient")
    def test_authenticate_network_timeout(self, mock_client_class):
        """Test authentication failure due to network timeout"""
        mock_client = Mock()
        mock_client.login.side_effect = ConnectionError("Connection timeout")
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        result = client.authenticate()

        assert result is False
        assert client._authenticated is False

    @patch("src.bluesky_client.AtprotoClient")
    def test_authenticate_rate_limit_error(self, mock_client_class):
        """Test authentication failure due to rate limiting"""
        mock_client = Mock()
        mock_client.login.side_effect = Exception("Rate limit exceeded")
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        result = client.authenticate()

        assert result is False
        assert client._authenticated is False

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_recent_posts_network_error(self, mock_client_class):
        """Test get_recent_posts handling network errors gracefully"""
        mock_client = Mock()
        mock_client.get_author_feed.side_effect = ConnectionError("Network unreachable")
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True  # Simulate authenticated state

        # Should return empty result instead of crashing
        result = client.get_recent_posts()

        assert isinstance(result, type(client.get_recent_posts()))
        assert result.total_retrieved == 0

    @patch("src.bluesky_client.AtprotoClient")
    def test_get_post_thread_network_error(self, mock_client_class):
        """Test get_post_thread handling network errors gracefully"""
        mock_client = Mock()
        mock_client.get_post_thread.side_effect = ConnectionError("Network unreachable")
        mock_client_class.return_value = mock_client

        client = BlueskyClient("test.bsky.social", "test-password")
        client._authenticated = True  # Simulate authenticated state

        result = client.get_post_thread("at://test-uri")

        assert result is None
