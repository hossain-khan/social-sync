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

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file"""
        if not self.state_file.exists():
            return {
                "last_sync_time": None,
                "synced_posts": [],
                "last_bluesky_post_uri": None,
            }

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return (
                    data
                    if isinstance(data, dict)
                    else {
                        "last_sync_time": None,
                        "synced_posts": [],
                        "last_bluesky_post_uri": None,
                    }
                )
        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
            return {
                "last_sync_time": None,
                "synced_posts": [],
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

        # Keep only the last 100 synced posts to prevent file from growing too large
        if len(self.state["synced_posts"]) > 100:
            self.state["synced_posts"] = self.state["synced_posts"][-100:]

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
                return record.get("mastodon_id")
        return None

    def cleanup_old_records(self, days: int = 30):
        """Remove sync records older than specified days"""
        if "synced_posts" not in self.state:
            return

        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)

        filtered_posts = []
        for record in self.state["synced_posts"]:
            try:
                sync_time = datetime.fromisoformat(record["synced_at"])
                if sync_time.timestamp() > cutoff_date:
                    filtered_posts.append(record)
            except (KeyError, ValueError):
                # Keep records with invalid timestamps
                filtered_posts.append(record)

        removed_count = len(self.state["synced_posts"]) - len(filtered_posts)
        if removed_count > 0:
            self.state["synced_posts"] = filtered_posts
            self._save_state()
            logger.info(f"Cleaned up {removed_count} old sync records")
