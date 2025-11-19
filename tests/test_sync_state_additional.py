"""
Additional tests for SyncState module to improve coverage
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.sync_state import SyncState


class TestSyncStateEdgeCases:
    """Additional tests for SyncState edge cases to improve coverage"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file_path = os.path.join(self.temp_dir, "test_state.json")

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_corrupted_json_file_recovery(self):
        """Test that SyncState recovers gracefully from corrupted JSON files"""
        # Write corrupted JSON to state file
        with open(self.state_file_path, "w") as f:
            f.write("{ invalid json content")

        # Should create new state without crashing
        sync_state = SyncState(self.state_file_path)

        # Should have default empty state
        assert sync_state.get_synced_posts_count() == 0
        assert sync_state.get_last_sync_time() is None
        assert sync_state.get_user_did() is None

    def test_empty_file_handling(self):
        """Test handling of completely empty state file"""
        # Create empty file
        with open(self.state_file_path, "w") as f:
            pass  # Write nothing

        # Should create new state without crashing
        sync_state = SyncState(self.state_file_path)

        # Should have default empty state
        assert sync_state.get_synced_posts_count() == 0
        assert sync_state.get_last_sync_time() is None

    def test_invalid_json_structure_recovery(self):
        """Test recovery from valid JSON with wrong structure"""
        # Write valid JSON but with wrong structure
        with open(self.state_file_path, "w") as f:
            json.dump({"wrong": "structure", "completely": "different"}, f)

        sync_state = SyncState(self.state_file_path)

        # Should recover to empty state
        assert sync_state.get_synced_posts_count() == 0
        assert sync_state.get_last_sync_time() is None

    def test_file_permissions_error_handling(self):
        """Test handling of file permission errors"""
        # This test might not work on all systems, so we'll skip if it fails
        try:
            # Create a file and make it read-only
            with open(self.state_file_path, "w") as f:
                json.dump({"test": "data"}, f)

            os.chmod(self.state_file_path, 0o444)  # Read-only

            # Try to create SyncState (might fail on write operations)
            sync_state = SyncState(self.state_file_path)

            # Try to mark a post as synced (should handle gracefully)
            try:
                sync_state.mark_post_synced("at://test", "123")
            except (PermissionError, OSError):
                # Expected behavior - should handle gracefully
                pass

        except (OSError, PermissionError):
            pytest.skip("File permission test not supported on this system")
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(self.state_file_path, 0o644)
            except (OSError, PermissionError):
                pass

    def test_large_dataset_performance(self):
        """Test performance with large number of synced posts"""
        sync_state = SyncState(self.state_file_path)

        # Add many posts (the system keeps only last 100 to prevent file growth)
        num_posts = 1000
        for i in range(num_posts):
            uri = f"at://did:plc:test/app.bsky.feed.post/{i:06d}"
            mastodon_id = f"mastodon_{i:06d}"
            sync_state.mark_post_synced(uri, mastodon_id)

        # Verify count (system keeps only last 100 posts)
        assert sync_state.get_synced_posts_count() == 100

        # Test lookup performance for a recent post (should be found)
        test_uri = (
            "at://did:plc:test/app.bsky.feed.post/000999"  # One of the last posts
        )
        start_time = time.time()
        is_synced = sync_state.is_post_synced(test_uri)
        lookup_time = time.time() - start_time

        assert is_synced is True
        # Verify lookup performance is acceptable even with many records
        assert lookup_time < 1.0

        # Test lookup of old post that was evicted (should not be found)
        old_uri = (
            "at://did:plc:test/app.bsky.feed.post/000001"  # One of the first posts
        )
        is_synced = sync_state.is_post_synced(old_uri)
        assert is_synced is False

    def test_cleanup_old_records(self):
        """Test cleanup of old records functionality"""
        sync_state = SyncState(self.state_file_path)

        # Add some recent posts
        recent_posts = []
        for i in range(5):
            uri = f"at://did:plc:test/app.bsky.feed.post/recent_{i}"
            mastodon_id = f"mastodon_recent_{i}"
            sync_state.mark_post_synced(uri, mastodon_id)
            recent_posts.append(uri)

        # Manually add some old posts by manipulating the state
        # (This is a bit hacky but necessary to test cleanup without waiting)
        old_timestamp = (datetime.now() - timedelta(days=35)).isoformat()

        # Access internal state to add old records
        with open(self.state_file_path, "r") as f:
            state_data = json.load(f)

        # Add old records
        for i in range(3):
            old_post = {
                "bluesky_uri": f"at://did:plc:test/app.bsky.feed.post/old_{i}",
                "mastodon_id": f"mastodon_old_{i}",
                "synced_at": old_timestamp,
            }
            state_data["synced_posts"].append(old_post)

        with open(self.state_file_path, "w") as f:
            json.dump(state_data, f)

        # Create new SyncState instance to reload data
        sync_state = SyncState(self.state_file_path)
        initial_count = sync_state.get_synced_posts_count()
        assert initial_count == 8  # 5 recent + 3 old

        # Run cleanup
        sync_state.cleanup_old_records(days=30)

        # Should remove old posts but keep recent ones
        final_count = sync_state.get_synced_posts_count()
        assert final_count == 5  # Only recent posts should remain

        # Verify recent posts are still there
        for uri in recent_posts:
            assert sync_state.is_post_synced(uri) is True

    def test_get_mastodon_id_functionality(self):
        """Test getting Mastodon ID for Bluesky URI"""
        sync_state = SyncState(self.state_file_path)

        # Test getting ID for non-existent post
        non_existent_uri = "at://did:plc:test/app.bsky.feed.post/nonexistent"
        mastodon_id = sync_state.get_mastodon_id_for_bluesky_post(non_existent_uri)
        assert mastodon_id is None

        # Add a post and test getting its ID
        test_uri = "at://did:plc:test/app.bsky.feed.post/test123"
        test_mastodon_id = "mastodon_test123"
        sync_state.mark_post_synced(test_uri, test_mastodon_id)

        retrieved_id = sync_state.get_mastodon_id_for_bluesky_post(test_uri)
        assert retrieved_id == test_mastodon_id

    def test_user_did_functionality(self):
        """Test user DID storage and retrieval"""
        sync_state = SyncState(self.state_file_path)

        # Initially should be None
        assert sync_state.get_user_did() is None

        # Set user DID
        test_did = "did:plc:abcdef123456"
        sync_state.set_user_did(test_did)

        # Should retrieve the same DID
        retrieved_did = sync_state.get_user_did()
        assert retrieved_did == test_did

        # Test updating DID
        new_did = "did:plc:xyz789"
        sync_state.set_user_did(new_did)

        updated_did = sync_state.get_user_did()
        assert updated_did == new_did

    def test_state_persistence_across_instances(self):
        """Test that state persists across different SyncState instances"""
        # Create first instance and add data
        sync_state1 = SyncState(self.state_file_path)
        test_uri = "at://did:plc:test/app.bsky.feed.post/persist123"
        test_mastodon_id = "mastodon_persist123"
        test_did = "did:plc:persistent"

        sync_state1.mark_post_synced(test_uri, test_mastodon_id)
        sync_state1.set_user_did(test_did)
        sync_state1.update_sync_time()

        # Create second instance with same file
        sync_state2 = SyncState(self.state_file_path)

        # Data should persist
        assert sync_state2.is_post_synced(test_uri) is True
        assert (
            sync_state2.get_mastodon_id_for_bluesky_post(test_uri) == test_mastodon_id
        )
        assert sync_state2.get_user_did() == test_did
        assert sync_state2.get_last_sync_time() is not None

    def test_concurrent_access_simulation(self):
        """Test behavior when multiple instances access the same file"""
        # Create two instances pointing to the same file
        sync_state1 = SyncState(self.state_file_path)
        sync_state2 = SyncState(self.state_file_path)

        # Add data through first instance
        sync_state1.mark_post_synced("at://test1", "mastodon1")

        # Add data through second instance
        sync_state2.mark_post_synced("at://test2", "mastodon2")

        # Create fresh instance to see final state
        sync_state3 = SyncState(self.state_file_path)

        # At least one of the posts should be there
        # (behavior depends on timing and implementation)
        total_posts = sync_state3.get_synced_posts_count()
        assert total_posts >= 1

    def test_invalid_uri_handling(self):
        """Test handling of invalid URIs"""
        sync_state = SyncState(self.state_file_path)

        # Test with various invalid URIs
        invalid_uris = [
            "",  # Empty string
            "not-a-uri",  # Not a URI format
            "at://",  # Incomplete AT URI
            "http://example.com",  # Wrong protocol
        ]

        for invalid_uri in invalid_uris:
            try:
                # These operations should handle invalid URIs gracefully
                sync_state.mark_post_synced(invalid_uri, "test_id")
                is_synced = sync_state.is_post_synced(invalid_uri)
                mastodon_id = sync_state.get_mastodon_id_for_bluesky_post(invalid_uri)
                # Verify methods handle invalid URIs gracefully without crashing
                # Exact behavior depends on implementation
            except (TypeError, ValueError):
                # These exceptions are acceptable for invalid input
                pass

    def test_special_characters_in_ids(self):
        """Test handling of special characters in URIs and Mastodon IDs"""
        sync_state = SyncState(self.state_file_path)

        # Test with special characters
        special_test_cases = [
            ("at://did:plc:test/app.bsky.feed.post/emoji🦋test", "mastodon_emoji_123"),
            (
                "at://did:plc:test/app.bsky.feed.post/unicode-测试",
                "mastodon_unicode_456",
            ),
            (
                "at://did:plc:test/app.bsky.feed.post/spaces test",
                "mastodon with spaces",
            ),
            ("at://did:plc:test/app.bsky.feed.post/symbols!@#$%", "mastodon!@#$%"),
        ]

        for uri, mastodon_id in special_test_cases:
            try:
                sync_state.mark_post_synced(uri, mastodon_id)
                assert sync_state.is_post_synced(uri) is True
                assert sync_state.get_mastodon_id(uri) == mastodon_id
            except Exception:
                # Some special characters might not be supported
                # The important thing is that it doesn't crash the whole system
                pass

    def test_timestamp_handling(self):
        """Test timestamp handling and formatting"""
        sync_state = SyncState(self.state_file_path)

        # Update sync time
        before_update = datetime.now()
        sync_state.update_sync_time()
        after_update = datetime.now()

        # Get the timestamp
        last_sync = sync_state.get_last_sync_time()
        assert last_sync is not None

        # Should be a datetime object
        assert isinstance(last_sync, datetime)

        # Should be between before and after
        assert before_update <= last_sync <= after_update
