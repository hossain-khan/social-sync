"""
Main sync orchestrator for Social Sync
"""

import logging
import time
from datetime import datetime
from typing import List, Tuple

from .bluesky_client import BlueskyClient, BlueskyFetchResult, BlueskyPost
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

    def get_posts_to_sync(self) -> Tuple[List[BlueskyPost], int]:
        """Get new posts from Bluesky that haven't been synced yet

        Returns:
            Tuple of (list of posts to sync, count of posts skipped with #no-sync tag)
        """
        logger.info("Fetching recent posts from Bluesky...")

        # Get the sync start date from configuration
        since_date = self.settings.get_sync_start_datetime()
        logger.info(f"Looking for posts since: {since_date.isoformat()}")

        fetch_result: BlueskyFetchResult = self.bluesky_client.get_recent_posts(
            limit=self.settings.max_posts_per_sync, since_date=since_date
        )

        # Log filtering statistics
        if fetch_result.total_retrieved > 0:
            logger.info(
                f"Retrieved {fetch_result.total_retrieved} total posts from Bluesky API"
            )
            if fetch_result.filtered_replies > 0:
                logger.info(
                    f"Filtered out {fetch_result.filtered_replies} reply posts in threads started by others"
                )
            if fetch_result.filtered_reposts > 0:
                logger.info(f"Filtered out {fetch_result.filtered_reposts} reposts")
            if fetch_result.filtered_by_date > 0:
                logger.info(
                    f"Filtered out {fetch_result.filtered_by_date} posts older than {since_date.isoformat()}"
                )

        # Filter out posts that have already been synced or skipped
        new_posts = []
        skipped_with_tag_count = 0
        already_skipped_count = 0

        for post in fetch_result.posts:
            # Check if already synced
            if self.sync_state.is_post_synced(post.uri):
                continue

            # Check if already skipped previously
            if self.sync_state.is_post_skipped(post.uri):
                already_skipped_count += 1
                continue

            # Check if post has #no-sync tag
            if self.content_processor.has_no_sync_tag(post.text):
                logger.info(f"Skipping post with #no-sync tag: {post.uri}")
                self.sync_state.mark_post_skipped(post.uri, reason="no-sync-tag")
                skipped_with_tag_count += 1
                continue

            new_posts.append(post)

        # Sort posts by creation time (ascending) to post older posts first
        new_posts.sort(key=lambda post: post.created_at)

        if skipped_with_tag_count > 0:
            logger.info(f"Skipped {skipped_with_tag_count} posts with #no-sync tag")
        if already_skipped_count > 0:
            logger.info(
                f"Found {already_skipped_count} posts that were previously skipped"
            )

        logger.info(f"Found {len(new_posts)} new posts to sync")
        return new_posts, skipped_with_tag_count

    def sync_post(self, bluesky_post: BlueskyPost) -> bool:
        """Sync a single post from Bluesky to Mastodon"""
        try:
            logger.info(f"Syncing post: {bluesky_post.uri}")

            # Check if this is a reply and find the parent post in Mastodon
            in_reply_to_id = None
            if bluesky_post.reply_to:
                # Look for the parent post's Mastodon ID in our sync state
                in_reply_to_id = self.sync_state.get_mastodon_id_for_bluesky_post(
                    bluesky_post.reply_to
                )
                if in_reply_to_id:
                    logger.info(
                        f"Post is a reply to {bluesky_post.reply_to}, will post as reply to Mastodon post {in_reply_to_id}"
                    )
                else:
                    logger.warning(
                        f"Post is a reply to {bluesky_post.reply_to}, but parent post not found in sync state. Posting as standalone."
                    )

            # Check if we have images to sync
            has_images = bool(
                self.content_processor.extract_images_from_embed(bluesky_post.embed)
            )

            # Process content for Mastodon compatibility
            # Don't include image placeholders if we're going to attach actual images
            processed_text = self.content_processor.process_bluesky_to_mastodon(
                text=bluesky_post.text,
                embed=bluesky_post.embed,
                facets=bluesky_post.facets,
                include_image_placeholders=not has_images or self.settings.dry_run,
            )

            # Add sync attribution (but not for replies to keep them concise)
            # and only if not disabled via configuration
            if not in_reply_to_id and not self.settings.disable_source_platform:
                processed_text = self.content_processor.add_sync_attribution(
                    processed_text
                )

            # Handle image attachments
            media_ids = []
            if bluesky_post.embed and not self.settings.dry_run:
                media_ids = self._sync_images(bluesky_post)

            # Check for content warnings if enabled in config
            is_sensitive = False
            spoiler_text = None
            if self.settings.sync_content_warnings:
                is_sensitive, spoiler_text = (
                    self.content_processor.get_content_warning_from_labels(
                        bluesky_post.self_labels
                    )
                )

                if is_sensitive:
                    logger.info(f"Applying content warning: {spoiler_text}")

            # Determine primary language (take first if multiple)
            # Bluesky allows multiple languages, Mastodon supports one
            language = None
            if bluesky_post.langs and len(bluesky_post.langs) > 0:
                language = bluesky_post.langs[0]
                logger.debug(f"Using language tag: {language}")

            if self.settings.dry_run:
                # Show what would be synced
                image_count = len(
                    self.content_processor.extract_images_from_embed(bluesky_post.embed)
                )
                image_info = f" with {image_count} image(s)" if image_count > 0 else ""
                reply_info = f" as reply to {in_reply_to_id}" if in_reply_to_id else ""
                cw_info = f" [CW: {spoiler_text}]" if is_sensitive else ""
                logger.info(
                    f"DRY RUN - Would post to Mastodon: {processed_text[:100]}...{image_info}{reply_info}{cw_info}"
                )
                # Don't mark posts as synced during dry runs
                return True
            else:
                # Post to Mastodon with media attachments, reply info, content warnings, and language
                mastodon_response = self.mastodon_client.post_status(
                    processed_text,
                    in_reply_to_id=in_reply_to_id,
                    media_ids=media_ids if media_ids else None,
                    sensitive=is_sensitive,
                    spoiler_text=spoiler_text,
                    language=language,
                )
                if not mastodon_response:
                    logger.error(f"Failed to post to Mastodon: {bluesky_post.uri}")
                    return False

                mastodon_post_id = mastodon_response["id"]
                if in_reply_to_id:
                    logger.info(
                        f"Successfully synced reply to Mastodon: {mastodon_post_id} (reply to {in_reply_to_id})"
                    )
                else:
                    logger.info(
                        f"Successfully synced post to Mastodon: {mastodon_post_id}"
                    )

                # Mark as synced only for actual posts
                self.sync_state.mark_post_synced(bluesky_post.uri, mastodon_post_id)
                return True

        except Exception as e:
            logger.error(f"Error syncing post {bluesky_post.uri}: {e}")
            return False

    def _sync_images(self, bluesky_post: BlueskyPost) -> List[str]:
        """Download images from Bluesky and upload to Mastodon

        Returns list of media IDs for Mastodon
        """
        media_ids: List[str] = []

        # Extract image information from embed
        images = self.content_processor.extract_images_from_embed(bluesky_post.embed)

        if not images:
            return media_ids

        logger.info(f"Found {len(images)} image(s) to sync for post {bluesky_post.uri}")

        # Extract author DID from URI for blob downloads
        # Format: at://did:plc:abc123/app.bsky.feed.post/xyz789
        author_did = bluesky_post.author_handle  # We'll need the actual DID
        if bluesky_post.uri.startswith("at://"):
            author_did = bluesky_post.uri.split("/")[2]

        for i, image_info in enumerate(images):
            try:
                logger.info(
                    f"Processing image {i+1}/{len(images)} for post {bluesky_post.uri}"
                )

                # Download image from Bluesky
                image_data = None
                mime_type = image_info.get("mime_type", "image/jpeg")

                if image_info.get("blob_ref"):
                    # Download via AT Protocol blob API
                    image_data = self.bluesky_client.download_blob(
                        image_info["blob_ref"], author_did
                    )
                elif image_info.get("url"):
                    # Download from direct URL
                    image_data = self.content_processor.download_image(
                        image_info["url"]
                    )

                if not image_data:
                    logger.warning(
                        f"Failed to download image {i+1} for post {bluesky_post.uri}"
                    )
                    continue

                image_bytes, actual_mime_type = image_data
                mime_type = actual_mime_type or mime_type

                # Upload to Mastodon
                media_id = self.mastodon_client.upload_media(
                    media_file=image_bytes,
                    mime_type=mime_type,
                    description=image_info.get("alt", ""),
                )

                if media_id:
                    media_ids.append(media_id)
                    logger.info(
                        f"Successfully uploaded image {i+1}/{len(images)} to Mastodon: {media_id}"
                    )
                    # Add delay between image uploads to avoid rate limiting
                    if i < len(images) - 1:  # Don't delay after the last image
                        time.sleep(0.5)  # Shorter delay for images within the same post
                else:
                    logger.warning(
                        f"Failed to upload image {i+1} to Mastodon for post {bluesky_post.uri}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing image {i+1} for post {bluesky_post.uri}: {e}"
                )
                continue

        logger.info(
            f"Successfully processed {len(media_ids)}/{len(images)} images for post {bluesky_post.uri}"
        )
        return media_ids

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
                "skipped_count": 0,
                "duration": (datetime.now() - start_time).total_seconds(),
            }

        # Get posts to sync
        try:
            posts_to_sync, skipped_count = self.get_posts_to_sync()
        except Exception as e:
            logger.error(f"Failed to get posts to sync: {e}")
            return {
                "success": False,
                "error": f"Failed to get posts: {e}",
                "synced_count": 0,
                "skipped_count": 0,
                "duration": (datetime.now() - start_time).total_seconds(),
            }

        # Sync posts
        synced_count = 0
        failed_count = 0

        for post in posts_to_sync:
            if self.sync_post(post):
                synced_count += 1
                # Add delay between posts to avoid rate limiting
                if synced_count < len(posts_to_sync):  # Don't delay after the last post
                    logger.info("Waiting 1 second to avoid rate limiting...")
                    time.sleep(1)
            else:
                failed_count += 1

        # Update sync state only if posts were synced or skipped
        # This prevents unnecessary commits when nothing changed
        if synced_count > 0 or skipped_count > 0:
            self.sync_state.update_sync_time()

        # Clean up old records periodically
        if synced_count > 0:
            self.sync_state.cleanup_old_records()

        duration = (datetime.now() - start_time).total_seconds()

        result = {
            "success": True,
            "synced_count": synced_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
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
        skipped_count = self.sync_state.get_skipped_posts_count()

        return {
            "last_sync_time": last_sync.isoformat() if last_sync else None,
            "total_synced_posts": synced_count,
            "total_skipped_posts": skipped_count,
            "dry_run_mode": self.settings.dry_run,
        }
