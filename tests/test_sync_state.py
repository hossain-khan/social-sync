"""
Tests for Sync State Management
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.sync_state import SyncState


class TestSyncState:
    """Test suite for SyncState class"""

    def setup_method(self):
        """Set up test fixtures with temporary state file"""
        # Create temporary file for state
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.temp_file.close()
        self.state_file_path = self.temp_file.name
        self.sync_state = SyncState(self.state_file_path)

    def teardown_method(self):
        """Clean up test fixtures"""
        if os.path.exists(self.state_file_path):
            os.unlink(self.state_file_path)

    def test_init_new_state_file(self):
        """Test initialization with non-existent state file"""
        # Remove the temp file to test creation
        os.unlink(self.state_file_path)

        SyncState(self.state_file_path)
        assert os.path.exists(self.state_file_path)

        # Check default structure
        with open(self.state_file_path, "r") as f:
            state_data = json.load(f)

        assert "last_sync_time" in state_data
        assert "synced_posts" in state_data
        assert "last_bluesky_post_uri" in state_data
        assert state_data["synced_posts"] == []

    def test_init_existing_state_file(self):
        """Test initialization with existing state file"""
        # Create initial state
        initial_state = {
            "last_sync_time": "2024-01-01T10:00:00",
            "synced_posts": [
                {
                    "bluesky_uri": "at://test-uri",
                    "mastodon_id": "12345",
                    "synced_at": "2024-01-01T10:00:00",
                }
            ],
            "last_bluesky_post_uri": "at://test-uri",
        }

        with open(self.state_file_path, "w") as f:
            json.dump(initial_state, f)

        # Initialize SyncState
        sync_state = SyncState(self.state_file_path)

        # Verify state loaded correctly
        assert sync_state.is_post_synced("at://test-uri")
        assert sync_state.get_synced_posts_count() == 1

    def test_is_post_synced_true(self):
        """Test checking if a post is synced (exists)"""
        # Add a synced post
        self.sync_state.mark_post_synced("at://test-uri", "12345")

        assert self.sync_state.is_post_synced("at://test-uri") is True

    def test_is_post_synced_false(self):
        """Test checking if a post is synced (doesn't exist)"""
        assert self.sync_state.is_post_synced("at://nonexistent-uri") is False

    def test_mark_post_synced(self):
        """Test marking a post as synced"""
        bluesky_uri = "at://test-uri"
        mastodon_id = "12345"

        self.sync_state.mark_post_synced(bluesky_uri, mastodon_id)

        # Verify post is marked as synced
        assert self.sync_state.is_post_synced(bluesky_uri)

        # Verify state file is updated
        with open(self.state_file_path, "r") as f:
            state_data = json.load(f)

        assert len(state_data["synced_posts"]) == 1
        post_record = state_data["synced_posts"][0]
        assert post_record["bluesky_uri"] == bluesky_uri
        assert post_record["mastodon_id"] == mastodon_id
        assert post_record["synced_at"] is not None

    def test_mark_post_synced_duplicate(self):
        """Test marking the same post as synced twice"""
        bluesky_uri = "at://test-uri"
        mastodon_id = "12345"

        # Mark post twice
        self.sync_state.mark_post_synced(bluesky_uri, mastodon_id)
        self.sync_state.mark_post_synced(bluesky_uri, "67890")  # Different Mastodon ID

        # Should still only have one record
        assert self.sync_state.get_synced_posts_count() == 1

        # Should have the latest Mastodon ID
        mastodon_id_found = self.sync_state.get_mastodon_id_for_bluesky_post(
            bluesky_uri
        )
        assert mastodon_id_found == "67890"

    def test_get_mastodon_id_for_bluesky_post_exists(self):
        """Test getting Mastodon ID for existing Bluesky post"""
        bluesky_uri = "at://test-uri"
        mastodon_id = "12345"

        self.sync_state.mark_post_synced(bluesky_uri, mastodon_id)
        result = self.sync_state.get_mastodon_id_for_bluesky_post(bluesky_uri)

        assert result == mastodon_id

    def test_get_mastodon_id_for_bluesky_post_not_exists(self):
        """Test getting Mastodon ID for non-existent Bluesky post"""
        result = self.sync_state.get_mastodon_id_for_bluesky_post("at://nonexistent")
        assert result is None

    def test_get_last_sync_time_no_sync(self):
        """Test getting last sync time when no sync has occurred"""
        result = self.sync_state.get_last_sync_time()
        assert result is None

    def test_get_last_sync_time_with_sync(self):
        """Test getting last sync time after sync"""
        self.sync_state.update_sync_time()
        result = self.sync_state.get_last_sync_time()

        assert result is not None
        assert isinstance(result, datetime)
        # Should be very recent (within last minute)
        time_diff = datetime.now() - result
        assert time_diff.total_seconds() < 60

    def test_update_sync_time(self):
        """Test updating sync time"""
        # Initial state should have no sync time
        assert self.sync_state.get_last_sync_time() is None

        # Update sync time
        self.sync_state.update_sync_time()

        # Should now have a sync time
        last_sync = self.sync_state.get_last_sync_time()
        assert last_sync is not None

        # Verify it's saved to file
        with open(self.state_file_path, "r") as f:
            state_data = json.load(f)
        assert state_data["last_sync_time"] is not None

    def test_get_synced_posts_count_empty(self):
        """Test getting synced posts count when empty"""
        assert self.sync_state.get_synced_posts_count() == 0

    def test_get_synced_posts_count_with_posts(self):
        """Test getting synced posts count with posts"""
        self.sync_state.mark_post_synced("at://uri1", "123")
        self.sync_state.mark_post_synced("at://uri2", "456")
        self.sync_state.mark_post_synced("at://uri3", "789")

        assert self.sync_state.get_synced_posts_count() == 3

    def test_cleanup_old_records(self):
        """Test cleanup of old records"""
        # Add some old records
        old_time = "2020-01-01T10:00:00"
        recent_time = datetime.now().isoformat()

        # Manually add records with specific timestamps
        state_data = {
            "last_sync_time": recent_time,
            "synced_posts": [
                {
                    "bluesky_uri": "at://old-uri",
                    "mastodon_id": "123",
                    "synced_at": old_time,
                },
                {
                    "bluesky_uri": "at://recent-uri",
                    "mastodon_id": "456",
                    "synced_at": recent_time,
                },
            ],
            "last_bluesky_post_uri": "at://recent-uri",
        }

        with open(self.state_file_path, "w") as f:
            json.dump(state_data, f)

        # Reload state and cleanup
        self.sync_state = SyncState(self.state_file_path)
        initial_count = self.sync_state.get_synced_posts_count()

        # Cleanup with very short retention (should remove old records)
        self.sync_state.cleanup_old_records(days=1)

        final_count = self.sync_state.get_synced_posts_count()
        assert final_count < initial_count

    def test_get_user_did_none(self):
        """Test getting user DID when not set"""
        assert self.sync_state.get_user_did() is None

    def test_set_user_did(self):
        """Test setting user DID"""
        test_did = "did:plc:test123"
        self.sync_state.set_user_did(test_did)

        assert self.sync_state.get_user_did() == test_did

        # Verify saved to file
        with open(self.state_file_path, "r") as f:
            state_data = json.load(f)
        assert state_data.get("user_did") == test_did

    def test_clear_state(self):
        """Test clearing all state data"""
        # Add some data first
        self.sync_state.mark_post_synced("at://test", "123")
        self.sync_state.update_sync_time()
        self.sync_state.set_user_did("did:plc:test")

        # Verify data exists
        assert self.sync_state.get_synced_posts_count() > 0
        assert self.sync_state.get_last_sync_time() is not None
        assert self.sync_state.get_user_did() is not None

        # Clear state
        self.sync_state.clear_state()

        # Verify state is cleared
        assert self.sync_state.get_synced_posts_count() == 0
        assert self.sync_state.get_last_sync_time() is None
        assert self.sync_state.get_user_did() is None

    def test_state_file_persistence(self):
        """Test that state persists across instances"""
        bluesky_uri = "at://test-persistence"
        mastodon_id = "99999"

        # Mark post in first instance
        self.sync_state.mark_post_synced(bluesky_uri, mastodon_id)

        # Create new instance with same file
        new_sync_state = SyncState(self.state_file_path)

        # Verify persistence
        assert new_sync_state.is_post_synced(bluesky_uri)
        assert (
            new_sync_state.get_mastodon_id_for_bluesky_post(bluesky_uri) == mastodon_id
        )

    def test_invalid_json_recovery(self):
        """Test recovery from corrupted JSON state file"""
        # Write invalid JSON to state file
        with open(self.state_file_path, "w") as f:
            f.write("invalid json content")

        # Should create new state without crashing
        sync_state = SyncState(self.state_file_path)

        # Should have default empty state
        assert sync_state.get_synced_posts_count() == 0
        assert sync_state.get_last_sync_time() is None
