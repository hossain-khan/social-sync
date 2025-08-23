"""
Bluesky client wrapper for Social Sync
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from atproto import Client as AtprotoClient

logger = logging.getLogger(__name__)


@dataclass
class BlueskyPost:
    """Represents a Bluesky post with metadata"""

    uri: str
    cid: str
    text: str
    created_at: datetime
    author_handle: str
    author_display_name: Optional[str] = None
    reply_to: Optional[str] = None
    embed: Optional[Dict[str, Any]] = None


class BlueskyClient:
    """Wrapper for Bluesky AT Protocol client"""

    def __init__(self, handle: str, password: str):
        self.handle = handle
        self.password = password
        self.client = AtprotoClient()
        self._authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with Bluesky"""
        try:
            profile = self.client.login(self.handle, self.password)
            self._authenticated = True
            logger.info(
                f"Successfully authenticated as {profile.display_name} (@{profile.handle})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Bluesky: {e}")
            return False

    def get_recent_posts(
        self, limit: int = 10, since_date: Optional[datetime] = None
    ) -> List[BlueskyPost]:
        """Get recent posts from authenticated user's feed

        Args:
            limit: Maximum number of posts to retrieve
            since_date: Only return posts created after this date
        """
        if not self._authenticated:
            raise RuntimeError("Client not authenticated. Call authenticate() first.")

        try:
            # Get the user's own posts
            response = self.client.get_author_feed(
                actor=self.handle, limit=limit * 2  # Get more posts to filter by date
            )

            posts = []
            for feed_item in response.feed:
                post = feed_item.post

                # Skip reposts (when reason is not None) and replies
                if (
                    hasattr(feed_item, "reason") and feed_item.reason is not None
                ) or post.record.reply:
                    continue

                # Parse the post creation date
                created_at = datetime.fromisoformat(
                    post.record.created_at.replace("Z", "+00:00")
                )

                # Filter by date if specified
                if since_date and created_at < since_date:
                    continue

                bluesky_post = BlueskyPost(
                    uri=post.uri,
                    cid=post.cid,
                    text=post.record.text,
                    created_at=created_at,
                    author_handle=post.author.handle,
                    author_display_name=post.author.display_name,
                    reply_to=(
                        post.record.reply.parent.uri if post.record.reply else None
                    ),
                    embed=(
                        post.record.embed.__dict__
                        if hasattr(post.record, "embed") and post.record.embed
                        else None
                    ),
                )
                posts.append(bluesky_post)

                # Stop if we have enough posts
                if len(posts) >= limit:
                    break

            logger.info(
                f"Retrieved {len(posts)} posts from Bluesky"
                + (f" since {since_date.isoformat()}" if since_date else "")
            )
            return posts

        except Exception as e:
            logger.error(f"Failed to fetch posts from Bluesky: {e}")
            return []

    def get_post_thread(self, post_uri: str) -> Optional[Dict[str, Any]]:
        """Get post thread context"""
        try:
            response = self.client.get_post_thread(uri=post_uri)
            thread = response.thread
            return thread if isinstance(thread, dict) else None
        except Exception as e:
            logger.error(f"Failed to fetch post thread: {e}")
            return None

    def download_blob(self, blob_ref: str, did: str) -> Optional[Tuple[bytes, str]]:
        """Download image blob from AT Protocol

        Args:
            blob_ref: The blob reference (CID)
            did: The DID of the post author

        Returns:
            Tuple of (image_bytes, mime_type) or None if failed
        """
        if not self._authenticated:
            logger.error("Client not authenticated for blob download")
            return None

        try:
            # Construct blob URL - AT Protocol blob service
            # Format: https://bsky.social/xrpc/com.atproto.sync.getBlob?did={did}&cid={blob_ref}
            blob_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={did}&cid={blob_ref}"

            headers = {"User-Agent": "Social-Sync/1.0 (AT Protocol blob downloader)"}

            # Add authentication if available
            if hasattr(self.client, "access_token") and self.client.access_token:
                headers["Authorization"] = f"Bearer {self.client.access_token}"

            response = requests.get(blob_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Get mime type from response headers
            mime_type = response.headers.get("content-type", "image/jpeg")
            if not mime_type.startswith("image/"):
                mime_type = "image/jpeg"

            logger.info(
                f"Successfully downloaded blob {blob_ref[:8]}... ({len(response.content)} bytes)"
            )
            return response.content, mime_type

        except Exception as e:
            logger.error(f"Failed to download blob {blob_ref}: {e}")
            return None
