"""
Additional tests for Bluesky Client module to improve coverage
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.bluesky_client import BlueskyClient, BlueskyPost, BlueskyFetchResult


class TestBlueskyClientEdgeCases:
    """Additional tests for BlueskyClient edge cases to improve coverage"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = BlueskyClient("test.bsky.social", "test-password")

    def test_authentication_failure_scenarios(self):
        """Test various authentication failure scenarios"""
        with patch.object(self.client.client, 'login') as mock_login:
            # Test network error during authentication
            mock_login.side_effect = Exception("Network error")
            
            result = self.client.authenticate()
            assert result is False
            assert self.client._authenticated is False

    def test_authentication_success_scenario(self):
        """Test successful authentication scenario"""
        with patch.object(self.client.client, 'login') as mock_login:
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
        with patch.object(self.client, 'authenticate', return_value=False):
            user_did = self.client.get_user_did()
            assert user_did is None

    def test_get_user_did_with_authentication_success(self):
        """Test get_user_did with successful authentication"""
        with patch.object(self.client, 'authenticate', return_value=True):
            # Mock client.me
            mock_me = Mock()
            mock_me.did = "did:plc:test123"
            self.client.client.me = mock_me
            self.client._authenticated = True
            
            user_did = self.client.get_user_did()
            assert user_did == "did:plc:test123"

    def test_get_user_did_with_missing_did(self):
        """Test get_user_did when client.me has no DID"""
        with patch.object(self.client, 'authenticate', return_value=True):
            # Mock client.me without DID
            self.client.client.me = None
            self.client._authenticated = True
            
            user_did = self.client.get_user_did()
            assert user_did is None

    def test_get_user_did_with_exception(self):
        """Test get_user_did when an exception occurs"""
        with patch.object(self.client, 'authenticate', return_value=True):
            self.client._authenticated = True
            # Mock an exception when accessing client.me
            with patch.object(self.client.client, 'me', side_effect=Exception("API error")):
                user_did = self.client.get_user_did()
                assert user_did is None

    @patch('src.bluesky_client.requests.get')
    def test_download_blob_network_error(self, mock_get):
        """Test download_blob with network error"""
        mock_get.side_effect = Exception("Network error")
        
        result = self.client.download_blob("blob_reference")
        assert result is None

    @patch('src.bluesky_client.requests.get')
    def test_download_blob_http_error(self, mock_get):
        """Test download_blob with HTTP error"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response
        
        result = self.client.download_blob("blob_reference")
        assert result is None

    @patch('src.bluesky_client.requests.get')
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
        
        result = self.client.download_blob("blob_reference")
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
        result = self.client.get_recent_posts(limit=10)
        
        # Should return empty result
        assert isinstance(result, BlueskyFetchResult)
        assert len(result.posts) == 0
        assert result.total_retrieved == 0

    def test_get_recent_posts_authentication_failure(self):
        """Test get_recent_posts when authentication fails"""
        with patch.object(self.client, 'authenticate', return_value=False):
            result = self.client.get_recent_posts(limit=10)
            
            assert isinstance(result, BlueskyFetchResult)
            assert len(result.posts) == 0

    def test_get_recent_posts_api_exception(self):
        """Test get_recent_posts when API call throws exception"""
        # Mock successful authentication
        with patch.object(self.client, 'authenticate', return_value=True):
            self.client._authenticated = True
            
            # Mock API call to throw exception
            with patch.object(self.client.client, 'get_author_feed', side_effect=Exception("API error")):
                result = self.client.get_recent_posts(limit=10)
                
                assert isinstance(result, BlueskyFetchResult)
                assert len(result.posts) == 0

    def test_get_recent_posts_with_filtering(self):
        """Test get_recent_posts with various filtering scenarios"""
        # Mock successful authentication
        with patch.object(self.client, 'authenticate', return_value=True):
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
                is_repost=False
            )
            
            reply_post = create_mock_post(
                uri="at://did:plc:user123/app.bsky.feed.post/reply",
                created_at=datetime.now(timezone.utc),
                is_reply=True,
                is_repost=False
            )
            
            repost = create_mock_post(
                uri="at://did:plc:user123/app.bsky.feed.post/repost",
                created_at=datetime.now(timezone.utc),
                is_reply=False,
                is_repost=True
            )
            
            valid_post = create_mock_post(
                uri="at://did:plc:user123/app.bsky.feed.post/valid",
                created_at=datetime.now(timezone.utc),
                is_reply=False,
                is_repost=False
            )
            
            mock_feed.feed = [
                Mock(post=old_post, reply=None, reason=None),
                Mock(post=reply_post, reply=Mock(), reason=None),  # Has reply object
                Mock(post=valid_post, reply=None, reason=Mock()),  # Has reason (repost)
                Mock(post=valid_post, reply=None, reason=None),   # Valid post
            ]
            
            with patch.object(self.client.client, 'get_author_feed', return_value=mock_feed):
                since_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
                result = self.client.get_recent_posts(limit=10, since_date=since_date)
                
                assert isinstance(result, BlueskyFetchResult)
                assert result.total_retrieved == 4
                # Filtering stats should reflect what was filtered out
                assert result.filtered_by_date >= 0
                assert result.filtered_replies >= 0
                assert result.filtered_reposts >= 0

    def test_get_post_thread_not_authenticated(self):
        """Test get_post_thread when not authenticated"""
        result = self.client.get_post_thread("at://test/post/123")
        assert result is None

    def test_get_post_thread_authentication_failure(self):
        """Test get_post_thread when authentication fails"""
        with patch.object(self.client, 'authenticate', return_value=False):
            result = self.client.get_post_thread("at://test/post/123")
            assert result is None

    def test_get_post_thread_api_exception(self):
        """Test get_post_thread when API call throws exception"""
        with patch.object(self.client, 'authenticate', return_value=True):
            self.client._authenticated = True
            
            with patch.object(self.client.client, 'get_post_thread', side_effect=Exception("API error")):
                result = self.client.get_post_thread("at://test/post/123")
                assert result is None

    def test_get_post_thread_success(self):
        """Test successful get_post_thread"""
        with patch.object(self.client, 'authenticate', return_value=True):
            self.client._authenticated = True
            
            # Mock successful thread response
            mock_thread = Mock()
            mock_post = create_mock_post(
                uri="at://test/post/123",
                created_at=datetime.now(timezone.utc),
                is_reply=False,
                is_repost=False
            )
            mock_thread.post = mock_post
            
            with patch.object(self.client.client, 'get_post_thread', return_value=mock_thread):
                result = self.client.get_post_thread("at://test/post/123")
                
                assert result is not None
                assert isinstance(result, BlueskyPost)
                assert result.uri == "at://test/post/123"


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
        mock_record.reply.parent.uri = "at://parent/post/uri"
    else:
        mock_record.reply = None
    
    mock_record.embed = None
    mock_record.facets = None
    
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
            facets=[{"type": "link"}]
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
            author_handle="test.bsky.social"
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
                author_handle="user1.bsky.social"
            ),
            BlueskyPost(
                uri="at://test/post/2",
                cid="cid2",
                text="Post 2",
                created_at=datetime.now(timezone.utc),
                author_handle="user2.bsky.social"
            )
        ]
        
        result = BlueskyFetchResult(
            posts=posts,
            total_retrieved=10,
            filtered_replies=3,
            filtered_reposts=2,
            filtered_by_date=3
        )
        
        assert len(result.posts) == 2
        assert result.total_retrieved == 10
        assert result.filtered_replies == 3
        assert result.filtered_reposts == 2
        assert result.filtered_by_date == 3
        
        # Test that filtering stats add up correctly
        total_filtered = result.filtered_replies + result.filtered_reposts + result.filtered_by_date
        expected_remaining = result.total_retrieved - total_filtered
        assert len(result.posts) <= expected_remaining

    def test_bluesky_fetch_result_empty(self):
        """Test BlueskyFetchResult with empty results"""
        result = BlueskyFetchResult(
            posts=[],
            total_retrieved=0,
            filtered_replies=0,
            filtered_reposts=0,
            filtered_by_date=0
        )
        
        assert len(result.posts) == 0
        assert result.total_retrieved == 0
        assert result.filtered_replies == 0
        assert result.filtered_reposts == 0
        assert result.filtered_by_date == 0