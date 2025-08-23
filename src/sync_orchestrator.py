"""
Main sync orchestrator for Social Sync
"""

import logging
from datetime import datetime
from typing import List

from .bluesky_client import BlueskyClient, BlueskyPost
from .config import get_settings
from .content_processor import ContentProcessor
from .mastodon_client import MastodonClient
from .sync_state import SyncState

logger = logging.getLogger(__name__)


class SocialSyncOrchestrator:
    """Main orchestrator for syncing posts between platforms"""

    def __init__(self):
        self.settings = get_settings()
        self.bluesky_client = None
        self.mastodon_client = None
        self.sync_state = SyncState(self.settings.state_file)
        self.content_processor = ContentProcessor()

    def setup_clients(self) -> bool:
        """Initialize and authenticate clients"""
        logger.info("Setting up clients...")

        # Initialize Bluesky client
        self.bluesky_client = BlueskyClient(
            handle=self.settings.bluesky_handle, password=self.settings.bluesky_password
        )

        if not self.bluesky_client.authenticate():
            logger.error("Failed to authenticate with Bluesky")
            return False

        # Initialize Mastodon client
        self.mastodon_client = MastodonClient(
            api_base_url=self.settings.mastodon_api_base_url,
            access_token=self.settings.mastodon_access_token,
        )

        if not self.mastodon_client.authenticate():
            logger.error("Failed to authenticate with Mastodon")
            return False

        logger.info("All clients authenticated successfully")
        return True

    def get_posts_to_sync(self) -> List[BlueskyPost]:
        """Get new posts from Bluesky that haven't been synced yet"""
        logger.info("Fetching recent posts from Bluesky...")

        # Get the sync start date from configuration
        since_date = self.settings.get_sync_start_datetime()
        logger.info(f"Looking for posts since: {since_date.isoformat()}")

        recent_posts = self.bluesky_client.get_recent_posts(
            limit=self.settings.max_posts_per_sync, since_date=since_date
        )

        # Filter out posts that have already been synced
        new_posts = []
        for post in recent_posts:
            if not self.sync_state.is_post_synced(post.uri):
                new_posts.append(post)

        logger.info(f"Found {len(new_posts)} new posts to sync")
        return new_posts

    def sync_post(self, bluesky_post: BlueskyPost) -> bool:
        """Sync a single post from Bluesky to Mastodon"""
        try:
            logger.info(f"Syncing post: {bluesky_post.uri}")

            # Process content for Mastodon compatibility
            processed_text = self.content_processor.process_bluesky_to_mastodon(
                text=bluesky_post.text, embed=bluesky_post.embed
            )

            # Add sync attribution
            processed_text = self.content_processor.add_sync_attribution(processed_text)

            if self.settings.dry_run:
                logger.info(
                    f"DRY RUN - Would post to Mastodon: {processed_text[:100]}..."
                )
                mastodon_post_id = "dry-run"
            else:
                # Post to Mastodon
                mastodon_response = self.mastodon_client.post_status(processed_text)
                if not mastodon_response:
                    logger.error(f"Failed to post to Mastodon: {bluesky_post.uri}")
                    return False

                mastodon_post_id = mastodon_response["id"]
                logger.info(f"Successfully synced post to Mastodon: {mastodon_post_id}")

            # Mark as synced
            self.sync_state.mark_post_synced(bluesky_post.uri, mastodon_post_id)
            return True

        except Exception as e:
            logger.error(f"Error syncing post {bluesky_post.uri}: {e}")
            return False

    def run_sync(self) -> dict:
        """Run the main sync process"""
        start_time = datetime.now()

        logger.info("Starting social sync process...")

        # Setup clients
        if not self.setup_clients():
            return {
                "success": False,
                "error": "Failed to setup clients",
                "synced_count": 0,
                "duration": (datetime.now() - start_time).total_seconds(),
            }

        # Get posts to sync
        try:
            posts_to_sync = self.get_posts_to_sync()
        except Exception as e:
            logger.error(f"Failed to get posts to sync: {e}")
            return {
                "success": False,
                "error": f"Failed to get posts: {e}",
                "synced_count": 0,
                "duration": (datetime.now() - start_time).total_seconds(),
            }

        # Sync posts
        synced_count = 0
        failed_count = 0

        for post in posts_to_sync:
            if self.sync_post(post):
                synced_count += 1
            else:
                failed_count += 1

        # Update sync state
        self.sync_state.update_sync_time()

        # Clean up old records periodically
        if synced_count > 0:
            self.sync_state.cleanup_old_records()

        duration = (datetime.now() - start_time).total_seconds()

        result = {
            "success": True,
            "synced_count": synced_count,
            "failed_count": failed_count,
            "total_processed": len(posts_to_sync),
            "duration": duration,
            "dry_run": self.settings.dry_run,
        }

        logger.info(
            f"Sync completed: {synced_count} synced, {failed_count} failed, {duration:.2f}s"
        )
        return result

    def get_sync_status(self) -> dict:
        """Get current sync status"""
        last_sync = self.sync_state.get_last_sync_time()
        synced_count = self.sync_state.get_synced_posts_count()

        return {
            "last_sync_time": last_sync.isoformat() if last_sync else None,
            "total_synced_posts": synced_count,
            "dry_run_mode": self.settings.dry_run,
        }
