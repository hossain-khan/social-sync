"""
Tests for Sync Orchestrator
"""
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.sync_orchestrator import SocialSyncOrchestrator
from src.bluesky_client import BlueskyPost


class TestSocialSyncOrchestrator:
    """Test suite for SocialSyncOrchestrator class"""

    def setup_method(self):
        """Set up test fixtures with mocked dependencies"""
        # Mock all the dependencies
        with patch('sync_orchestrator.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.bluesky_handle = 'test.bsky.social'
            mock_settings.bluesky_password = 'test-password'
            mock_settings.mastodon_api_base_url = 'https://mastodon.social'
            mock_settings.mastodon_access_token = 'test-token'
            mock_settings.max_posts_per_sync = 10
            mock_settings.dry_run = False
            mock_settings.state_file = 'test_state.json'
            mock_settings.get_sync_start_datetime.return_value = datetime(2025, 1, 1)
            mock_get_settings.return_value = mock_settings
            
            self.orchestrator = SocialSyncOrchestrator()
            self.orchestrator.settings = mock_settings

        # Mock clients and other dependencies
        self.mock_bluesky_client = Mock()
        self.mock_mastodon_client = Mock()
        self.mock_sync_state = Mock()
        self.mock_content_processor = Mock()
        
        self.orchestrator.bluesky_client = self.mock_bluesky_client
        self.orchestrator.mastodon_client = self.mock_mastodon_client  
        self.orchestrator.sync_state = self.mock_sync_state
        self.orchestrator.content_processor = self.mock_content_processor

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
        self.mock_bluesky_client.get_recent_posts.return_value = []
        
        result = self.orchestrator.get_posts_to_sync()
        
        assert result == []
        self.mock_bluesky_client.get_recent_posts.assert_called_once()

    def test_get_posts_to_sync_with_new_posts(self):
        """Test getting posts with new (unsynced) posts"""
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
            facets=[]
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
            facets=[]
        )
        
        self.mock_bluesky_client.get_recent_posts.return_value = [mock_post1, mock_post2]
        self.mock_sync_state.is_post_synced.return_value = False  # Neither post is synced
        
        result = self.orchestrator.get_posts_to_sync()
        
        assert len(result) == 2
        assert result[0].uri == "at://test-uri-1"  # Should be sorted by creation time
        assert result[1].uri == "at://test-uri-2"

    def test_get_posts_to_sync_filter_already_synced(self):
        """Test getting posts filters out already synced posts"""
        mock_post1 = BlueskyPost(
            uri="at://synced-uri",
            cid="test-cid-1",
            text="Already synced post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social", 
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[]
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
            facets=[]
        )
        
        self.mock_bluesky_client.get_recent_posts.return_value = [mock_post1, mock_post2]
        
        # Mock sync state: first post is synced, second is not
        def is_post_synced_side_effect(uri):
            return uri == "at://synced-uri"
        
        self.mock_sync_state.is_post_synced.side_effect = is_post_synced_side_effect
        
        result = self.orchestrator.get_posts_to_sync()
        
        assert len(result) == 1
        assert result[0].uri == "at://new-uri"

    def test_sync_post_simple_text_success(self):
        """Test syncing a simple text post successfully"""
        mock_post = BlueskyPost(
            uri="at://test-uri",
            cid="test-cid",
            text="Simple test post",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to=None,
            embed=None,
            facets=[]
        )
        
        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = "Processed text"
        self.mock_content_processor.add_sync_attribution.return_value = "Processed text\n\n(via Bluesky)"
        
        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = "mastodon-post-id-123"
        
        result = self.orchestrator.sync_post(mock_post)
        
        assert result is True
        self.mock_mastodon_client.post_status.assert_called_once()
        self.mock_sync_state.mark_post_synced.assert_called_once_with(
            "at://test-uri", "mastodon-post-id-123"
        )

    def test_sync_post_reply_with_parent_found(self):
        """Test syncing a reply post when parent is found"""
        mock_post = BlueskyPost(
            uri="at://reply-uri",
            cid="test-cid",
            text="This is a reply",
            created_at=datetime(2025, 1, 1, 10, 0), 
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://parent-uri",
            embed=None,
            facets=[]
        )
        
        # Mock finding parent post
        self.mock_sync_state.get_mastodon_id_for_bluesky_post.return_value = "parent-mastodon-id"
        
        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = "This is a reply"
        # Note: replies don't get sync attribution
        
        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = "reply-mastodon-id"
        
        result = self.orchestrator.sync_post(mock_post)
        
        assert result is True
        # Verify post_status called with in_reply_to_id
        self.mock_mastodon_client.post_status.assert_called_once()
        call_args = self.mock_mastodon_client.post_status.call_args
        assert call_args[1]['in_reply_to_id'] == "parent-mastodon-id"

    def test_sync_post_reply_parent_not_found(self):
        """Test syncing a reply post when parent is not found"""
        mock_post = BlueskyPost(
            uri="at://orphan-reply-uri",
            cid="test-cid",
            text="Orphaned reply",
            created_at=datetime(2025, 1, 1, 10, 0),
            author_handle="test.bsky.social",
            author_display_name="Test User",
            reply_to="at://missing-parent-uri",
            embed=None,
            facets=[]
        )
        
        # Mock parent not found
        self.mock_sync_state.get_mastodon_id_for_bluesky_post.return_value = None
        
        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = "Orphaned reply"
        self.mock_content_processor.add_sync_attribution.return_value = "Orphaned reply\n\n(via Bluesky)"
        
        # Mock Mastodon posting
        self.mock_mastodon_client.post_status.return_value = "orphan-mastodon-id"
        
        result = self.orchestrator.sync_post(mock_post)
        
        assert result is True
        # Should post as standalone (no in_reply_to_id)
        call_args = self.mock_mastodon_client.post_status.call_args
        assert 'in_reply_to_id' not in call_args[1] or call_args[1]['in_reply_to_id'] is None

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
            facets=[]
        )
        
        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = "Dry run post"
        self.mock_content_processor.add_sync_attribution.return_value = "Dry run post\n\n(via Bluesky)"
        
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
            facets=[]
        )
        
        # Mock content processing
        self.mock_content_processor.extract_images_from_embed.return_value = []
        self.mock_content_processor.process_bluesky_to_mastodon.return_value = "Error post"
        self.mock_content_processor.add_sync_attribution.return_value = "Error post\n\n(via Bluesky)"
        
        # Mock Mastodon posting failure
        self.mock_mastodon_client.post_status.side_effect = Exception("Mastodon API error")
        
        result = self.orchestrator.sync_post(mock_post)
        
        assert result is False
        # Should not mark as synced if posting fails
        self.mock_sync_state.mark_post_synced.assert_not_called()

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
                facets=[]
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
                facets=[]
            )
        ]
        
        self.mock_bluesky_client.get_recent_posts.return_value = mock_posts
        self.mock_sync_state.is_post_synced.return_value = False
        
        # Mock successful sync for both posts
        with patch.object(self.orchestrator, 'sync_post', return_value=True) as mock_sync_post:
            result = self.orchestrator.run_sync()
        
        assert result['success'] is True
        assert result['synced_count'] == 2
        assert result['failed_count'] == 0
        assert result['total_processed'] == 2
        assert result['dry_run'] == False
        assert isinstance(result['duration'], float)
        
        # Verify sync_post called for both posts
        assert mock_sync_post.call_count == 2
        self.mock_sync_state.update_sync_time.assert_called_once()
        self.mock_sync_state.cleanup_old_records.assert_called_once()

    def test_run_sync_client_setup_failure(self):
        """Test sync run with client setup failure"""
        self.mock_bluesky_client.authenticate.return_value = False
        
        result = self.orchestrator.run_sync()
        
        assert result['success'] is False
        assert result['error'] == "Failed to setup clients"
        assert result['synced_count'] == 0
        assert isinstance(result['duration'], float)

    def test_run_sync_no_posts(self):
        """Test sync run when no posts are available"""
        # Mock client setup success
        self.mock_bluesky_client.authenticate.return_value = True
        self.mock_mastodon_client.authenticate.return_value = True
        
        # Mock no posts to sync
        self.mock_bluesky_client.get_recent_posts.return_value = []
        
        result = self.orchestrator.run_sync()
        
        assert result['success'] is True
        assert result['synced_count'] == 0
        assert result['failed_count'] == 0
        assert result['total_processed'] == 0
        
        # Should still update sync time even with no posts
        self.mock_sync_state.update_sync_time.assert_called_once()

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
                facets=[]
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
                facets=[]
            )
        ]
        
        self.mock_bluesky_client.get_recent_posts.return_value = mock_posts
        self.mock_sync_state.is_post_synced.return_value = False
        
        # Mock mixed success/failure
        def sync_post_side_effect(post):
            return post.uri == "at://success-post"
        
        with patch.object(self.orchestrator, 'sync_post', side_effect=sync_post_side_effect):
            result = self.orchestrator.run_sync()
        
        assert result['success'] is True
        assert result['synced_count'] == 1
        assert result['failed_count'] == 1
        assert result['total_processed'] == 2

    def test_get_sync_status(self):
        """Test getting sync status"""
        # Mock sync state
        mock_last_sync = datetime(2025, 1, 1, 12, 0)
        self.mock_sync_state.get_last_sync_time.return_value = mock_last_sync
        self.mock_sync_state.get_synced_posts_count.return_value = 42
        
        result = self.orchestrator.get_sync_status()
        
        assert result['last_sync_time'] == mock_last_sync.isoformat()
        assert result['total_synced_posts'] == 42
        assert result['dry_run_mode'] == False

    def test_get_sync_status_no_previous_sync(self):
        """Test getting sync status when no previous sync exists"""
        self.mock_sync_state.get_last_sync_time.return_value = None
        self.mock_sync_state.get_synced_posts_count.return_value = 0
        
        result = self.orchestrator.get_sync_status()
        
        assert result['last_sync_time'] is None
        assert result['total_synced_posts'] == 0
        assert result['dry_run_mode'] == False
