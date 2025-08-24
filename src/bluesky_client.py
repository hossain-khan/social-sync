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
    facets: Optional[List[Dict[str, Any]]] = None


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

    def get_user_did(self) -> Optional[str]:
        """Get the authenticated user's DID"""
        if not self._authenticated:
            if not self.authenticate():
                return None

        try:
            return (
                str(self.client.me.did)
                if self.client.me and self.client.me.did
                else None
            )
        except Exception as e:
            logger.error(f"Failed to get user DID: {e}")
            return None

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
            # Get the user's own posts (AT Protocol max is 100)
            actual_limit = min(limit * 2, 100)  # Ensure we don't exceed API limit
            response = self.client.get_author_feed(
                actor=self.handle, limit=actual_limit
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
                        BlueskyClient._extract_embed_data(post.record.embed)
                        if hasattr(post.record, "embed") and post.record.embed
                        else None
                    ),
                    facets=(
                        BlueskyClient._extract_facets_data(post.record.facets)
                        if hasattr(post.record, "facets") and post.record.facets
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

    @staticmethod
    def _extract_facets_data(facets) -> List[Dict[str, Any]]:
        """Extract facets data into dictionaries for easier processing"""
        try:
            facets_data: List[Dict[str, Any]] = []
            for facet in facets:
                facet_dict: Dict[str, Any] = {
                    "index": {
                        "byteStart": facet.index.byte_start,
                        "byteEnd": facet.index.byte_end,
                    },
                    "features": [],
                }

                # Extract features (links, mentions, hashtags, etc.)
                if hasattr(facet, "features") and facet.features:
                    for feature in facet.features:
                        feature_dict: Dict[str, Any] = {
                            "py_type": str(type(feature).__name__)
                        }

                        # Extract link URI if it's a link feature
                        if hasattr(feature, "uri"):
                            feature_dict["uri"] = feature.uri

                        facet_dict["features"].append(feature_dict)

                facets_data.append(facet_dict)

            return facets_data
        except Exception as e:
            logger.warning(f"Error extracting facets data: {e}")
            return []

    @staticmethod
    def _extract_embed_data(embed) -> Optional[Dict[str, Any]]:
        """Extract embed data into dictionary for easier processing"""
        try:
            embed_dict: Dict[str, Any] = {
                "py_type": (
                    embed.py_type
                    if hasattr(embed, "py_type")
                    else str(type(embed).__name__)
                )
            }

            # Handle external embeds (link cards)
            if hasattr(embed, "external") and embed.external:
                external = embed.external
                embed_dict["external"] = {
                    "uri": getattr(external, "uri", None),
                    "title": getattr(external, "title", None),
                    "description": getattr(external, "description", None),
                }

            # Handle image embeds
            if hasattr(embed, "images") and embed.images:
                images_data = []
                for image in embed.images:
                    image_data = {
                        "alt": getattr(image, "alt", None),
                        "aspect_ratio": getattr(image, "aspect_ratio", None),
                    }
                    if hasattr(image, "image") and image.image:
                        image_data["image"] = {
                            "mime_type": getattr(image.image, "mime_type", None),
                            "size": getattr(image.image, "size", None),
                        }
                    images_data.append(image_data)
                embed_dict["images"] = images_data

            # Handle record embeds (quotes)
            if hasattr(embed, "record") and embed.record:
                # This would need more detailed handling for quote posts
                embed_dict["record"] = {"py_type": str(type(embed.record).__name__)}

            return embed_dict
        except Exception as e:
            logger.warning(f"Error extracting embed data: {e}")
            return None

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
