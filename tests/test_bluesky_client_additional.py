"""
Additional tests for Bluesky Client module to improve coverage
"""

from datetime import datetime, timezone
from unittest.mock import Mock, PropertyMock, patch

import pytest

from src.bluesky_client import BlueskyClient, BlueskyFetchResult, BlueskyPost


class TestBlueskyClientEdgeCases:
    """Additional tests for BlueskyClient edge cases to improve coverage"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = BlueskyClient("test.bsky.social", "test-password")

    def test_authentication_failure_scenarios(self):
        """Test various authentication failure scenarios"""
        with patch.object(self.client.client, "login") as mock_login:
            # Test network error during authentication
            mock_login.side_effect = Exception("Network error")

            result = self.client.authenticate()
            assert result is False
            assert self.client._authenticated is False

    def test_authentication_success_scenario(self):
        """Test successful authentication scenario"""
        with patch.object(self.client.client, "login") as mock_login:
            # Mock successful authentication
            mock_profile = Mock()
            mock_profile.display_name = "Test User"
            mock_profile.handle = "test.bsky.social"
            mock_login.return_value = mock_profile

            result = self.client.authenticate()
            assert result is True
            assert self.client._authenticated is True

    def test_get_user_did_without_authentication(self):
        """Test get_user_did when not authenticated"""
        # Mock authentication failure
        with patch.object(self.client, "authenticate", return_value=False):
            user_did = self.client.get_user_did()
            assert user_did is None

    def test_get_user_did_with_authentication_success(self):
        """Test get_user_did with successful authentication"""
        with patch.object(self.client, "authenticate", return_value=True):
            # Mock client.me
            mock_me = Mock()
            mock_me.did = "did:plc:test123"
            self.client.client.me = mock_me
            self.client._authenticated = True

            user_did = self.client.get_user_did()
            assert user_did == "did:plc:test123"

    def test_get_user_did_with_missing_did(self):
        """Test get_user_did when client.me has no DID"""
        with patch.object(self.client, "authenticate", return_value=True):
            # Mock client.me without DID
            self.client.client.me = None
            self.client._authenticated = True

            user_did = self.client.get_user_did()
            assert user_did is None

    def test_get_user_did_with_exception(self):
        """Test get_user_did when an exception occurs"""
        with patch.object(self.client, "authenticate", return_value=True):
            self.client._authenticated = True
            # Mock an exception when accessing client.me property
            mock_client = Mock()
            # Configure the mock to raise an exception when .me is accessed
            type(mock_client).me = PropertyMock(side_effect=Exception("API error"))
            self.client.client = mock_client

            user_did = self.client.get_user_did()
            assert user_did is None

    @patch("src.bluesky_client.requests.get")
    def test_download_blob_network_error(self, mock_get):
        """Test download_blob with network error"""
        mock_get.side_effect = Exception("Network error")

        result = self.client.download_blob("blob_reference", "did:plc:test123")
        assert result is None

    @patch("src.bluesky_client.requests.get")
    def test_download_blob_http_error(self, mock_get):
        """Test download_blob with HTTP error"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response

        result = self.client.download_blob("blob_reference", "did:plc:test123")
        assert result is None

    @patch("src.bluesky_client.requests.get")
    def test_download_blob_success(self, mock_get):
        """Test successful blob download"""
        mock_response = Mock()
        mock_response.content = b"blob data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Mock authenticated client
        self.client._authenticated = True
        self.client.client.me = Mock()
        self.client.client.me.did = "did:plc:test"

        result = self.client.download_blob("blob_reference", "did:plc:test123")
        assert result == (b"blob data", "image/jpeg")

    def test_extract_did_from_uri_various_formats(self):
        """Test _extract_did_from_uri with various URI formats"""
        test_cases = [
            ("at://did:plc:abc123/app.bsky.feed.post/xyz", "did:plc:abc123"),
            ("at://did:web:example.com/app.bsky.feed.post/123", "did:web:example.com"),
            ("at://invalid-did-format/path", None),  # Invalid format
            ("invalid-uri", None),  # Not an AT URI
            ("", None),  # Empty string
            ("at://", None),  # Incomplete URI
        ]

        for uri, expected_did in test_cases:
            result = self.client._extract_did_from_uri(uri)
            assert result == expected_did

    def test_get_recent_posts_not_authenticated(self):
        """Test get_recent_posts when not authenticated"""
        with pytest.raises(RuntimeError) as exc_info:
            self.client.get_recent_posts(limit=10)

        assert "not authenticated" in str(exc_info.value)

    def test_get_recent_posts_authentication_failure(self):
        """Test get_recent_posts raises RuntimeError when client was never authenticated"""
        with pytest.raises(RuntimeError) as exc_info:
            self.client.get_recent_posts(limit=10)

        assert "not authenticated" in str(exc_info.value)

    def test_get_recent_posts_api_exception(self):
        """Test get_recent_posts when API call throws exception"""
        # Mock successful authentication
        with patch.object(self.client, "authenticate", return_value=True):
            self.client._authenticated = True

            # Mock API call to throw exception
            with patch.object(
                self.client.client,
                "get_author_feed",
                side_effect=Exception("API error"),
            ):
                result = self.client.get_recent_posts(limit=10)

                assert isinstance(result, BlueskyFetchResult)
                assert len(result.posts) == 0

    def test_get_recent_posts_with_filtering(self):
        """Test get_recent_posts with various filtering scenarios"""
        # Mock successful authentication
        with patch.object(self.client, "authenticate", return_value=True):
            self.client._authenticated = True
            self.client.client.me = Mock()
            self.client.client.me.did = "did:plc:user123"

            # Create mock feed data with various post types
            mock_feed = Mock()

            # Create different types of posts for filtering
            old_post = create_mock_post(
                uri="at://did:plc:user123/app.bsky.feed.post/old",
                created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                is_reply=False,
                is_repost=False,
            )

            reply_post = create_mock_post(
                uri="at://did:plc:user123/app.bsky.feed.post/reply",
                created_at=datetime.now(timezone.utc),
                is_reply=True,
                is_repost=False,
            )

            valid_post = create_mock_post(
                uri="at://did:plc:user123/app.bsky.feed.post/valid",
                created_at=datetime.now(timezone.utc),
                is_reply=False,
                is_repost=False,
            )

            mock_feed.feed = [
                Mock(post=old_post, reply=None, reason=None),
                Mock(post=reply_post, reply=Mock(), reason=None),  # Has reply object
                Mock(post=valid_post, reply=None, reason=Mock()),  # Has reason (repost)
                Mock(post=valid_post, reply=None, reason=None),  # Valid post
            ]

            with patch.object(
                self.client.client, "get_author_feed", return_value=mock_feed
            ):
                since_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
                result = self.client.get_recent_posts(limit=10, since_date=since_date)

                assert isinstance(result, BlueskyFetchResult)
                assert result.total_retrieved == 4
                # Verify exact filtering counts: 1 old post, 1 reply, 1 repost, 1 included
                assert result.filtered_by_date == 1
                assert result.filtered_replies == 1
                assert result.filtered_reposts == 1
                assert result.filtered_quotes == 0
                assert len(result.posts) == 1

    def test_get_post_thread_not_authenticated(self):
        """Test get_post_thread when not authenticated"""
        result = self.client.get_post_thread("at://test/post/123")
        assert result is None

    def test_get_post_thread_authentication_failure(self):
        """Test get_post_thread when authentication fails"""
        with patch.object(self.client, "authenticate", return_value=False):
            result = self.client.get_post_thread("at://test/post/123")
            assert result is None

    def test_get_post_thread_api_exception(self):
        """Test get_post_thread when API call throws exception"""
        with patch.object(self.client, "authenticate", return_value=True):
            self.client._authenticated = True

            with patch.object(
                self.client.client,
                "get_post_thread",
                side_effect=Exception("API error"),
            ):
                result = self.client.get_post_thread("at://test/post/123")
                assert result is None

    def test_get_post_thread_success(self):
        """Test successful get_post_thread"""
        with patch.object(self.client, "authenticate", return_value=True):
            self.client._authenticated = True

            # Mock successful thread response
            mock_response = Mock()
            mock_thread = {"thread": {"post": {"uri": "at://test/post/123"}}}
            mock_response.thread = mock_thread

            with patch.object(
                self.client.client, "get_post_thread", return_value=mock_response
            ):
                result = self.client.get_post_thread("at://test/post/123")

                assert result is not None
                assert isinstance(result, dict)
                assert "thread" in result


def create_mock_post(uri, created_at, is_reply=False, is_repost=False):
    """Helper function to create mock post objects"""
    mock_post = Mock()
    mock_post.uri = uri
    mock_post.cid = "test_cid"

    # Mock record
    mock_record = Mock()
    mock_record.text = "Test post content"
    mock_record.created_at = created_at.isoformat()

    if is_reply:
        mock_record.reply = Mock()
        mock_record.reply.parent = Mock()
        mock_record.reply.parent.uri = (
            "at://did:plc:otheruser/app.bsky.feed.post/parent"
        )
        # Add root attribute for reply detection
        mock_record.reply.root = Mock()
        mock_record.reply.root.uri = "at://did:plc:otheruser/app.bsky.feed.post/root"
    else:
        mock_record.reply = None

    mock_record.embed = None
    mock_record.facets = None
    mock_record.labels = None  # Add labels attribute
    mock_record.langs = None  # Add langs attribute

    mock_post.record = mock_record

    # Mock author
    mock_author = Mock()
    mock_author.handle = "test.bsky.social"
    mock_author.display_name = "Test User"
    mock_post.author = mock_author

    return mock_post


class TestBlueskyDataClasses:
    """Test the Bluesky dataclasses"""

    def test_bluesky_post_creation(self):
        """Test BlueskyPost dataclass creation"""
        now = datetime.now(timezone.utc)

        post = BlueskyPost(
            uri="at://test/post/123",
            cid="test_cid",
            text="Test post",
            created_at=now,
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://parent/post/456",
            embed={"type": "external", "uri": "https://example.com"},
            facets=[{"type": "link"}],
        )

        assert post.uri == "at://test/post/123"
        assert post.cid == "test_cid"
        assert post.text == "Test post"
        assert post.created_at == now
        assert post.author_handle == "test.bsky.social"
        assert post.author_display_name == "Test User"
        assert post.reply_to == "at://parent/post/456"
        assert post.embed is not None
        assert post.facets is not None

    def test_bluesky_post_minimal_creation(self):
        """Test BlueskyPost creation with minimal required fields"""
        now = datetime.now(timezone.utc)

        post = BlueskyPost(
            uri="at://test/post/123",
            cid="test_cid",
            text="Test post",
            created_at=now,
            author_handle="test.bsky.social",
        )

        assert post.uri == "at://test/post/123"
        assert post.author_display_name is None
        assert post.reply_to is None
        assert post.embed is None
        assert post.facets is None

    def test_bluesky_fetch_result_creation(self):
        """Test BlueskyFetchResult dataclass creation"""
        posts = [
            BlueskyPost(
                uri="at://test/post/1",
                cid="cid1",
                text="Post 1",
                created_at=datetime.now(timezone.utc),
                author_handle="user1.bsky.social",
            ),
            BlueskyPost(
                uri="at://test/post/2",
                cid="cid2",
                text="Post 2",
                created_at=datetime.now(timezone.utc),
                author_handle="user2.bsky.social",
            ),
        ]

        result = BlueskyFetchResult(
            posts=posts,
            total_retrieved=10,
            filtered_replies=3,
            filtered_reposts=2,
            filtered_by_date=3,
        )

        assert len(result.posts) == 2
        assert result.total_retrieved == 10
        assert result.filtered_replies == 3
        assert result.filtered_reposts == 2
        assert result.filtered_by_date == 3

        # Test that filtering stats add up correctly
        total_filtered = (
            result.filtered_replies + result.filtered_reposts + result.filtered_by_date
        )
        expected_remaining = result.total_retrieved - total_filtered
        assert len(result.posts) <= expected_remaining

    def test_bluesky_fetch_result_empty(self):
        """Test BlueskyFetchResult with empty results"""
        result = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        assert len(result.posts) == 0
        assert result.total_retrieved == 0
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0

    def test_bluesky_fetch_result_filtered_posts_default(self):
        """Test that filtered_posts defaults to an empty dict (not None) when omitted"""
        result = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        # Must be an empty dict, never None, so callers can call .items() safely
        assert result.filtered_posts == {}
        assert isinstance(result.filtered_posts, dict)

    def test_bluesky_fetch_result_filtered_posts_are_per_instance(self):
        """Test that each BlueskyFetchResult instance gets its own filtered_posts dict"""
        result_a = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )
        result_b = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
        )

        result_a.filtered_posts["at://user/post/1"] = "reply-not-self-threaded"

        # Mutation of one instance must not affect the other
        assert "at://user/post/1" not in result_b.filtered_posts

    def test_dataclass_initialization_no_filtered_posts(self):
        """Test initialization when filtered_posts is None"""
        result = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0,
            filtered_quotes=0,
            filtered_posts=None,
        )
        assert result.filtered_posts == {}


class TestBlueskyClientAdditional:
    """Additional tests for BlueskyClient"""

    def test_extract_did_from_uri_empty_identifier(self):
        """Test extracting DID from URI with empty identifier"""
        client = BlueskyClient("test.bsky.social", "test-password")
        assert (
            client._extract_did_from_uri("at://did:plc:/app.bsky.feed.post/12345")
            is None
        )

    def test_get_recent_posts_malformed_uri_in_reply(self):
        """Test handling malformed URIs in reply"""
        mock_client = Mock()
        mock_me = Mock()
        mock_me.did = "did:plc:test123"
        mock_client.me = mock_me

        mock_reply = Mock()
        mock_reply.root = Mock()
        mock_reply.root.uri = "malformed:uri"
        mock_reply.parent = Mock()
        mock_reply.parent.uri = "another:malformed:uri"

        mock_post_record = Mock()
        mock_post_record.text = "This is a reply"
        mock_post_record.created_at = "2025-01-01T10:00:00.000Z"
        mock_post_record.facets = []
        mock_post_record.reply = mock_reply
        mock_post_record.labels = None
        mock_post_record.langs = None
        if hasattr(mock_post_record, "embed"):
            delattr(mock_post_record, "embed")

        mock_feed_item = Mock()
        if hasattr(mock_feed_item, "reason"):
            delattr(mock_feed_item, "reason")

        mock_feed_item.post = Mock()
        mock_feed_item.post.uri = "at://did:plc:test123/app.bsky.feed.post/12345"
        mock_feed_item.post.cid = "test-cid"
        mock_feed_item.post.record = mock_post_record
        mock_feed_item.post.author = Mock()
        mock_feed_item.post.author.handle = "test.bsky.social"
        mock_feed_item.post.author.display_name = "Test User"
        if hasattr(mock_feed_item.post, "embed"):
            delattr(mock_feed_item.post, "embed")

        mock_response = Mock()
        mock_response.feed = [mock_feed_item]
        mock_client.get_author_feed.return_value = mock_response

        client = BlueskyClient("test.bsky.social", "test-password")
        client.client = mock_client
        client._authenticated = True

        result = client.get_recent_posts()
        assert result.filtered_replies == 1
        assert (
            result.filtered_posts["at://did:plc:test123/app.bsky.feed.post/12345"]
            == "reply-not-self-threaded"
        )

    def test_extract_facets_data_exception(self):
        """Test extract_facets_data exception handling"""
        mock_facet = Mock()
        # Mock index but make it raise exception when accessed
        type(mock_facet).index = property(
            lambda self: (_ for _ in ()).throw(Exception("Test error"))
        )

        result = BlueskyClient._extract_facets_data([mock_facet])
        assert result == []

    def test_extract_embed_data_image_ref_dict(self):
        """Test extract embed data with dict image ref"""
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.images"

        mock_image = Mock()
        mock_image.alt = "Test alt"
        mock_image_blob = Mock()
        mock_image_blob.mime_type = "image/jpeg"
        mock_image_blob.size = 1234
        # Use simple dict for ref to test fallback branch
        mock_image_blob.ref = {"somedata": "value"}
        if hasattr(mock_image_blob.ref, "link"):
            delattr(mock_image_blob.ref, "link")
        if hasattr(mock_image_blob.ref, "$link"):
            delattr(mock_image_blob.ref, "$link")

        mock_image.image = mock_image_blob
        mock_embed.images = [mock_image]
        if hasattr(mock_embed, "external"):
            delattr(mock_embed, "external")
        if hasattr(mock_embed, "media"):
            delattr(mock_embed, "media")
        if hasattr(mock_embed, "video"):
            delattr(mock_embed, "video")
        if hasattr(mock_embed, "record"):
            delattr(mock_embed, "record")

        result = BlueskyClient._extract_embed_data(mock_embed)
        assert result is not None
        assert result["images"][0]["image"]["ref"] == {"somedata": "value"}

    def test_extract_embed_data_video_ref_fallback(self):
        """Test extract embed data video ref fallback to str"""
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.video"

        mock_video = Mock()
        mock_video_blob = Mock()
        mock_video_blob.mime_type = "video/mp4"
        mock_video_blob.size = 1234

        class MockRefFallback:
            def __str__(self):
                return "justastring"

        mock_video_blob.ref = MockRefFallback()

        mock_video.ref = MockRefFallback()
        mock_video.mime_type = "video/mp4"
        mock_video.size = 1234
        if hasattr(mock_video, "video"):
            delattr(mock_video, "video")
        mock_embed.video = mock_video
        if hasattr(mock_embed, "external"):
            delattr(mock_embed, "external")
        if hasattr(mock_embed, "images"):
            delattr(mock_embed, "images")
        if hasattr(mock_embed, "media"):
            delattr(mock_embed, "media")
        if hasattr(mock_embed, "record"):
            delattr(mock_embed, "record")

        result = BlueskyClient._extract_embed_data(mock_embed)
        assert result is not None
        assert result["video"]["blob_ref"] == "justastring"

    @patch("src.bluesky_client.requests.get")
    def test_download_blob_fallback_mime_type(self, mock_get):
        """Test download blob fallback to image/jpeg mime type"""
        mock_response = Mock()
        mock_response.content = b"fakeimage"
        # Return a content type that doesn't start with image/
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_get.return_value = mock_response

        client = BlueskyClient("test.bsky.social", "test-password")
        client.client = Mock()  # mock client so hasattr doesn't fail
        client.client.access_token = "fake_token"
        client._authenticated = True

        result = client.download_blob("fake_blob", "did:plc:123")
        assert result is not None
        assert result[1] == "image/jpeg"

    def test_download_video_unauthenticated(self):
        """Test download video unauthenticated returns None instead of raising ValueError (it logs an error)"""
        client = BlueskyClient("test.bsky.social", "test-password")
        # client is not authenticated
        result = client.download_video("fake_blob", "did:plc:123")
        assert result is None

    @patch("src.bluesky_client.requests.get")
    def test_download_video_exception(self, mock_get):
        """Test download video handling exceptions"""
        mock_get.side_effect = Exception("Test exception")

        client = BlueskyClient("test.bsky.social", "test-password")
        client.client = Mock()
        client.client.access_token = "fake_token"
        client._authenticated = True

        result = client.download_video("fake_blob", "did:plc:123")
        assert result is None

    def test_download_blob_unauthenticated(self):
        """Test download blob unauthenticated returns None"""
        client = BlueskyClient("test.bsky.social", "test-password")
        # client is not authenticated
        result = client.download_blob("fake_blob", "did:plc:123")
        assert result is None

    @patch("src.bluesky_client.requests.get")
    def test_download_video_success(self, mock_get):
        """Test download video successful"""
        mock_response = Mock()
        mock_response.content = b"fakevideo"
        mock_response.headers = {"content-type": "video/webm"}
        mock_get.return_value = mock_response

        client = BlueskyClient("test.bsky.social", "test-password")
        client.client = Mock()
        client.client.access_token = "fake_token"
        client._authenticated = True

        result = client.download_video("fake_blob", "did:plc:123")
        assert result is not None
        assert result[0] == b"fakevideo"
        assert result[1] == "video/webm"

    @patch("src.bluesky_client.requests.get")
    def test_download_video_success_no_token(self, mock_get):
        """Test download video successful without token"""
        mock_response = Mock()
        mock_response.content = b"fakevideo"
        mock_response.headers = {"content-type": "video/webm"}
        mock_get.return_value = mock_response

        client = BlueskyClient("test.bsky.social", "test-password")
        client.client = Mock()
        client.client.access_token = None
        client._authenticated = True

        result = client.download_video("fake_blob", "did:plc:123")
        assert result is not None

    def test_extract_did_from_uri_exception(self):
        """Test extract did from uri handling index error internally without crashing if split behaves unexpectedly"""
        client = BlueskyClient("test.bsky.social", "test-password")
        # Providing something that triggers an AttributeError when split() is called
        result = client._extract_did_from_uri(None)
        assert result is None

    def test_extract_did_from_uri_invalid_start(self):
        """Test extract did from uri not starting with did:"""
        client = BlueskyClient("test.bsky.social", "test-password")
        assert (
            client._extract_did_from_uri("at://notadid:12345/app.bsky.feed.post/123")
            is None
        )

    def test_extract_did_from_uri_less_than_3_parts(self):
        """Test extract did from uri with less than 3 parts"""
        client = BlueskyClient("test.bsky.social", "test-password")
        assert (
            client._extract_did_from_uri("at://did:plc/app.bsky.feed.post/123") is None
        )

    def test_extract_embed_data_image_ref_dict_fallback(self):
        """Test extract embed data with dict image ref that uses $link internally (not hasattr)"""
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.images"

        mock_image = Mock()
        mock_image.alt = "Test alt"
        mock_image_blob = Mock()
        mock_image_blob.mime_type = "image/jpeg"
        mock_image_blob.size = 1234

        # We need a dict-like mock for the ref
        # so hasattr(ref, "$link") fails, but we want it to act like a dict with "$link"
        # Wait, the code says: `elif hasattr(ref, "$link"):`
        # if `hasattr` is true, it goes to `ref["$link"]`
        class MockRefDollarLink:
            def __getitem__(self, key):
                return "some_link_value"

        ref = MockRefDollarLink()
        setattr(ref, "$link", True)  # Make hasattr return True
        if hasattr(ref, "link"):
            delattr(ref, "link")
        mock_image_blob.ref = ref

        mock_image.image = mock_image_blob
        mock_embed.images = [mock_image]
        if hasattr(mock_embed, "external"):
            delattr(mock_embed, "external")
        if hasattr(mock_embed, "media"):
            delattr(mock_embed, "media")
        if hasattr(mock_embed, "video"):
            delattr(mock_embed, "video")
        if hasattr(mock_embed, "record"):
            delattr(mock_embed, "record")

        result = BlueskyClient._extract_embed_data(mock_embed)
        assert result is not None
        assert result["images"][0]["image"]["ref"]["$link"] == "some_link_value"

    def test_extract_embed_data_video_ref_dict_fallback(self):
        """Test extract embed data video ref fallback to dict with $link"""
        mock_embed = Mock()
        mock_embed.py_type = "app.bsky.embed.video"

        mock_video = Mock()
        mock_video.mime_type = "video/mp4"
        mock_video.size = 1234

        mock_video.ref = {"$link": "dict_link_val"}

        if hasattr(mock_video, "video"):
            delattr(mock_video, "video")
        mock_embed.video = mock_video
        if hasattr(mock_embed, "external"):
            delattr(mock_embed, "external")
        if hasattr(mock_embed, "images"):
            delattr(mock_embed, "images")
        if hasattr(mock_embed, "media"):
            delattr(mock_embed, "media")
        if hasattr(mock_embed, "record"):
            delattr(mock_embed, "record")

        result = BlueskyClient._extract_embed_data(mock_embed)
        assert result is not None
        assert result["video"]["blob_ref"] == "dict_link_val"

    def test_extract_did_from_uri_index_error(self):
        """Test extract did from uri handling IndexError internally"""
        client = BlueskyClient("test.bsky.social", "test-password")

        # Pass a custom mock string that raises IndexError on split
        class MockString(str):
            def split(self, *args, **kwargs):
                raise IndexError("test index error")

            def startswith(self, prefix):
                return True

        assert client._extract_did_from_uri(MockString("did:something")) is None

    def test_extract_did_from_uri_attribute_error(self):
        """Test extract did from uri handling AttributeError internally"""
        client = BlueskyClient("test.bsky.social", "test-password")
        # Trigger an attribute error by passing an object that lacks `startswith` or `split`
        assert client._extract_did_from_uri(123) is None
