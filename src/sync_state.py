"""
State management for Social Sync
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SyncState:
    """Manages sync state to avoid duplicate posts"""

    def __init__(self, state_file: str = "sync_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
        # If file didn't exist, save the initial state
        if not self.state_file.exists():
            self._save_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file"""
        if not self.state_file.exists():
            return {
                "last_sync_time": None,
                "synced_posts": [],
                "skipped_posts": [],
                "last_bluesky_post_uri": None,
            }

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                # Ensure skipped_posts field exists for backward compatibility
                if isinstance(data, dict):
                    if "skipped_posts" not in data:
                        data["skipped_posts"] = []
                    return data
                else:
                    return {
                        "last_sync_time": None,
                        "synced_posts": [],
                        "skipped_posts": [],
                        "last_bluesky_post_uri": None,
                    }
        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
            return {
                "last_sync_time": None,
                "synced_posts": [],
                "skipped_posts": [],
                "last_bluesky_post_uri": None,
            }

    def _save_state(self):
        """Save state to file"""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2, default=str)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def is_post_synced(self, post_uri: str) -> bool:
        """Check if a post has already been synced"""
        synced_posts = self.state.get("synced_posts", [])
        for record in synced_posts:
            if isinstance(record, dict) and record.get("bluesky_uri") == post_uri:
                return True
            elif (
                isinstance(record, str) and record == post_uri
            ):  # Backward compatibility
                return True
        return False

    def mark_post_synced(
        self, bluesky_post_uri: str, mastodon_post_id: Optional[str] = None
    ):
        """Mark a post as synced"""
        if "synced_posts" not in self.state:
            self.state["synced_posts"] = []

        sync_record = {
            "bluesky_uri": bluesky_post_uri,
            "mastodon_id": mastodon_post_id,
            "synced_at": datetime.now().isoformat(),
        }

        # Remove existing record if it exists
        self.state["synced_posts"] = [
            record
            for record in self.state["synced_posts"]
            if record.get("bluesky_uri") != bluesky_post_uri
        ]

        self.state["synced_posts"].append(sync_record)

        self.state["last_bluesky_post_uri"] = bluesky_post_uri
        self._save_state()

    def update_sync_time(self):
        """Update the last sync time"""
        self.state["last_sync_time"] = datetime.now().isoformat()
        self._save_state()

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last sync time"""
        last_sync = self.state.get("last_sync_time")
        if last_sync:
            try:
                return datetime.fromisoformat(last_sync)
            except ValueError:
                return None
        return None

    def get_synced_posts_count(self) -> int:
        """Get the number of synced posts"""
        return len(self.state.get("synced_posts", []))

    def get_mastodon_id_for_bluesky_post(self, bluesky_uri: str) -> Optional[str]:
        """Get the Mastodon post ID for a given Bluesky URI"""
        synced_posts = self.state.get("synced_posts", [])
        for record in synced_posts:
            if isinstance(record, dict) and record.get("bluesky_uri") == bluesky_uri:
                mastodon_id = record.get("mastodon_id")
                return mastodon_id if isinstance(mastodon_id, str) else None
        return None

    def cleanup_old_records(self, days: int = 30):
        """Remove sync records older than specified days

        DEPRECATED: This method is deprecated and no longer performs any cleanup.
        Sync state records are now preserved indefinitely to maintain complete history.
        This method is kept for backward compatibility only.

        Args:
            days: Previously used to specify retention period (now ignored)
        """
        logger.warning(
            "cleanup_old_records() is deprecated and no longer performs cleanup. "
            "All sync state records are now preserved indefinitely."
        )
        return

    def get_user_did(self) -> Optional[str]:
        """Get the stored user DID"""
        user_did = self.state.get("user_did")
        return user_did if isinstance(user_did, str) else None

    def set_user_did(self, user_did: str):
        """Set the user DID"""
        self.state["user_did"] = user_did
        self._save_state()

    def clear_state(self):
        """Clear all state data"""
        self.state = {
            "last_sync_time": None,
            "synced_posts": [],
            "skipped_posts": [],
            "last_bluesky_post_uri": None,
        }
        self._save_state()

    def is_post_skipped(self, post_uri: str) -> bool:
        """Check if a post has been skipped due to #no-sync tag"""
        skipped_posts = self.state.get("skipped_posts", [])
        for record in skipped_posts:
            if isinstance(record, dict) and record.get("bluesky_uri") == post_uri:
                return True
            elif isinstance(record, str) and record == post_uri:
                return True
        return False

    def mark_post_skipped(self, bluesky_post_uri: str, reason: str = "no-sync-tag"):
        """Mark a post as skipped

        Args:
            bluesky_post_uri: The URI of the Bluesky post
            reason: The reason for skipping (default: "no-sync-tag")
        """
        if "skipped_posts" not in self.state:
            self.state["skipped_posts"] = []

        skip_record = {
            "bluesky_uri": bluesky_post_uri,
            "reason": reason,
            "skipped_at": datetime.now().isoformat(),
        }

        # Remove existing record if it exists
        self.state["skipped_posts"] = [
            record
            for record in self.state["skipped_posts"]
            if record.get("bluesky_uri") != bluesky_post_uri
        ]

        self.state["skipped_posts"].append(skip_record)

        self._save_state()

    def get_skipped_posts_count(self) -> int:
        """Get the number of skipped posts"""
        return len(self.state.get("skipped_posts", []))
