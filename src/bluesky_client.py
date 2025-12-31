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
class BlueskyFetchResult:
    """
    Result of fetching posts from Bluesky with filtering statistics.

    This provides visibility into how many posts were retrieved vs filtered,
    including detailed information about filtered posts for audit trail.
    """

    posts: List["BlueskyPost"]
    total_retrieved: int  # Total posts fetched from API
    filtered_replies: int  # Number of reply posts filtered out
    filtered_reposts: int  # Number of reposts filtered out
    filtered_by_date: int  # Number of posts filtered by date
    filtered_quotes: int = 0  # Number of quote posts of others filtered out

    # Detailed filtering information for audit trail
    filtered_posts: Dict[str, str] = None  # Dict mapping post URI -> filter reason

    def __post_init__(self):
        """Initialize filtered_posts if not provided"""
        if self.filtered_posts is None:
            self.filtered_posts = {}


@dataclass
class BlueskyPost:
    """
    Represents a Bluesky post with metadata and rich content.

    This class normalizes AT Protocol post data into a format that can be
    easily processed for cross-platform synchronization.
    """

    uri: str  # Unique AT Protocol identifier (at://...)
    cid: str  # Content identifier hash
    text: str  # Plain text content of the post
    created_at: datetime  # Post creation timestamp
    author_handle: str  # Author's handle (e.g., "user.bsky.social")
    author_display_name: Optional[str] = None  # Author's display name
    reply_to: Optional[str] = None  # URI of parent post if this is a reply

    # Rich media attachments (external links, images, quoted posts)
    # Converted from AT Protocol objects to dicts for easier cross-platform processing
    embed: Optional[Dict[str, Any]] = None

    # Text formatting metadata (hashtags, mentions, links with precise positions)
    # Used to preserve rich text features when syncing to other platforms
    facets: Optional[List[Dict[str, Any]]] = None

    # Content warning labels (e.g., "porn", "nudity", "graphic-media", "sexual")
    # Used to apply content warnings when syncing to platforms like Mastodon
    self_labels: Optional[List[str]] = None

    # Language codes (ISO 639-1 two-letter codes, e.g., "en", "es", "ja")
    # Used for language-based filtering and i18n metadata preservation
    langs: Optional[List[str]] = None


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

    def _extract_did_from_uri(self, uri: str) -> Optional[str]:
        """Extract DID from AT Protocol URI

        Args:
            uri: AT Protocol URI like at://did:plc:abc123/app.bsky.feed.post/xyz

        Returns:
            DID string like "did:plc:abc123" or None if invalid
        """
        try:
            if not uri or not uri.startswith("at://"):
                return None

            # Remove at:// prefix and split by /
            path_part = uri[5:]  # Remove "at://"
            parts = path_part.split("/")

            if not parts or not parts[0]:
                return None

            did_candidate = parts[0]

            # Basic DID validation: should start with "did:" and have at least 3 parts
            if not did_candidate.startswith("did:"):
                return None

            did_parts = did_candidate.split(":")
            if len(did_parts) < 3:  # e.g., ["did", "plc", "identifier"]
                return None

            # Check that identifier is not empty
            if not did_parts[2]:  # Empty identifier like "did:plc:"
                return None

            return did_candidate

        except (IndexError, AttributeError):
            return None

    def get_recent_posts(
        self, limit: int = 10, since_date: Optional[datetime] = None
    ) -> BlueskyFetchResult:
        """Get recent posts from authenticated user's feed with filtering statistics

        Args:
            limit: Maximum number of posts to retrieve
            since_date: Only return posts created after this date

        Returns:
            BlueskyFetchResult with posts and filtering statistics
        """
        if not self._authenticated:
            raise RuntimeError("Client not authenticated. Call authenticate() first.")

        try:
            # Get user's DID for self-reply detection
            user_did = self.get_user_did()
            if not user_did:
                logger.warning("Could not get user DID for self-reply detection")

            # Get the user's own posts (AT Protocol max is 100)
            actual_limit = min(limit * 2, 100)  # Ensure we don't exceed API limit
            response = self.client.get_author_feed(
                actor=self.handle, limit=actual_limit
            )

            posts = []
            filtered_replies = 0
            filtered_reposts = 0
            filtered_by_date = 0
            filtered_quotes = 0
            filtered_posts = {}  # Track filtered posts with reasons
            total_retrieved = len(response.feed)

            for feed_item in response.feed:
                post = feed_item.post

                # Track and skip reposts
                if hasattr(feed_item, "reason") and feed_item.reason is not None:
                    filtered_reposts += 1
                    filtered_posts[post.uri] = "repost"
                    continue

                # Track and skip quote posts of other people's content
                # Allow self-quotes (quoting own posts) but filter quotes of others
                if hasattr(post.record, "embed") and post.record.embed:
                    embed_type = getattr(post.record.embed, "py_type", None)

                    # Check if this is a quote post (app.bsky.embed.record)
                    if embed_type == "app.bsky.embed.record":
                        # Extract the quoted post URI
                        if hasattr(post.record.embed, "record") and hasattr(
                            post.record.embed.record, "uri"
                        ):
                            quoted_uri = post.record.embed.record.uri
                            quoted_did = self._extract_did_from_uri(quoted_uri)

                            # Skip if quoting someone else's post (allow self-quotes)
                            if quoted_did and quoted_did != user_did:
                                filtered_quotes += 1
                                filtered_posts[post.uri] = "quote-of-other"
                                logger.debug(
                                    f"Filtered quote post of other's content: {post.uri} (quoting: {quoted_uri})"
                                )
                                continue
                            elif quoted_did == user_did:
                                logger.debug(
                                    f"Including self-quote post: {post.uri} (quoting own: {quoted_uri})"
                                )

                # Handle replies: only include self-replies where the root is by the user
                # AND the immediate parent is also by the user
                # Filter all replies in threads started by other people
                #
                # WHY: We only want to sync posts that are part of YOUR conversations,
                # not replies you make to other people's conversations. This prevents
                # syncing fragments of discussions with other users, which would be
                # out of context on the target platform.
                #
                # EXAMPLES:
                # ✅ SYNCED: You reply to your own post -> your reply to that reply
                # ❌ FILTERED: Someone replies to your post -> you reply to their reply
                # ❌ FILTERED: Someone's post -> you reply to it
                #
                # The critical check: BOTH root AND parent must be by the user.
                # Just checking the root isn't enough (see example #2 above).
                reply_parent_uri = None
                if post.record.reply:
                    reply_parent_uri = post.record.reply.parent.uri
                    reply_root_uri = post.record.reply.root.uri

                    # Extract the author DIDs to check if both root and parent are by the user
                    root_did = (
                        self._extract_did_from_uri(reply_root_uri)
                        if reply_root_uri
                        else None
                    )
                    parent_did = (
                        self._extract_did_from_uri(reply_parent_uri)
                        if reply_parent_uri
                        else None
                    )

                    # Only allow replies where BOTH conditions are met:
                    # 1. Root is by the user (original thread starter)
                    # 2. Immediate parent is by the user (direct conversation, not nested in others' replies)
                    #
                    # This filters out:
                    # - Replies to other people's original posts
                    # - Replies to other people's replies, even if in user's own thread
                    # - Replies in threads started by other people
                    if root_did != user_did or parent_did != user_did:
                        # Filter out replies that don't meet both conditions
                        filtered_replies += 1
                        filtered_posts[post.uri] = "reply-not-self-threaded"
                        logger.debug(
                            f"Filtered reply: {post.uri} (root: {reply_root_uri} by {root_did}, parent: {reply_parent_uri} by {parent_did})"
                        )
                        continue
                    else:
                        logger.debug(
                            f"Including self-reply: {post.uri} -> {reply_parent_uri} (root: {reply_root_uri})"
                        )

                # Parse the post creation date
                created_at = datetime.fromisoformat(
                    post.record.created_at.replace("Z", "+00:00")
                )

                # Filter by date if specified
                if since_date and created_at < since_date:
                    filtered_by_date += 1
                    filtered_posts[post.uri] = "older-than-sync-date"
                    continue

                # Extract self-labels (content warnings) if present
                self_labels = None
                if (
                    hasattr(post.record, "labels")
                    and post.record.labels
                    and hasattr(post.record.labels, "values")
                    and post.record.labels.values
                ):
                    self_labels = [label.val for label in post.record.labels.values]
                    logger.debug(f"Found self-labels: {self_labels}")

                # Extract language tags if present
                langs = None
                if hasattr(post.record, "langs") and post.record.langs:
                    langs = list(post.record.langs)
                    logger.debug(f"Found language tags: {langs}")

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
                    # Convert AT Protocol embed objects to dictionaries for cross-platform compatibility
                    # This ensures external links, images, etc. are preserved when syncing to Mastodon
                    embed=(
                        BlueskyClient._extract_embed_data(post.record.embed)
                        if hasattr(post.record, "embed") and post.record.embed
                        else None
                    ),
                    # Extract rich text features (hashtags, mentions, links) from AT Protocol facets
                    # Facets provide precise byte ranges and metadata for text formatting
                    facets=(
                        BlueskyClient._extract_facets_data(post.record.facets)
                        if hasattr(post.record, "facets") and post.record.facets
                        else None
                    ),
                    # Extract content warning labels for cross-platform moderation
                    self_labels=self_labels,
                    # Preserve language metadata for i18n support
                    langs=langs,
                )
                posts.append(bluesky_post)

                # Stop if we have enough posts
                if len(posts) >= limit:
                    break

            logger.info(
                f"Retrieved {len(posts)} posts from Bluesky"
                + (f" since {since_date.isoformat()}" if since_date else "")
            )
            if filtered_replies > 0:
                logger.info(
                    f"Filtered out {filtered_replies} reply posts in threads started by others"
                )
            if filtered_reposts > 0:
                logger.info(f"Filtered out {filtered_reposts} reposts")
            if filtered_by_date > 0:
                logger.info(f"Filtered out {filtered_by_date} posts by date")

            return BlueskyFetchResult(
                posts=posts,
                total_retrieved=total_retrieved,
                filtered_replies=filtered_replies,
                filtered_reposts=filtered_reposts,
                filtered_by_date=filtered_by_date,
                filtered_quotes=filtered_quotes,
                filtered_posts=filtered_posts,
            )

        except Exception as e:
            logger.error(f"Failed to fetch posts from Bluesky: {e}")
            return BlueskyFetchResult(
                posts=[],
                total_retrieved=0,
                filtered_replies=0,
                filtered_reposts=0,
                filtered_by_date=0,
                filtered_quotes=0,
                filtered_posts={},
            )

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
        """
        Extract embed data from AT Protocol embed objects into dictionaries.

        AT Protocol embeds are complex objects that contain rich media attachments
        like external links, images, or quoted posts. This method converts them
        into simple dictionaries that can be easily processed by the content
        processor when syncing to other platforms.

        Args:
            embed: AT Protocol embed object (can be External, Images, Record, etc.)

        Returns:
            Dictionary containing extracted embed data, or None if extraction fails

        Embed Types Handled:
        - External: Link cards with title, description, and URL
        - Images: Photo attachments with alt text and metadata
        - Video: Video attachments with metadata and blob references
        - Record: Quoted posts or other embedded records
        """
        try:
            # Start with the embed type identifier from AT Protocol
            # e.g., "app.bsky.embed.external" -> used by content processor for routing
            embed_dict: Dict[str, Any] = {
                "py_type": (
                    embed.py_type
                    if hasattr(embed, "py_type")
                    else str(type(embed).__name__)
                )
            }

            # === EXTERNAL LINKS (Link Cards) ===
            # These appear when users share URLs that generate preview cards
            # Example: Sharing a GitHub repo or news article link
            if hasattr(embed, "external") and embed.external:
                external = embed.external
                # Extract the three key pieces of link card data
                embed_dict["external"] = {
                    "uri": getattr(external, "uri", None),  # The actual URL
                    "title": getattr(external, "title", None),  # Page title
                    "description": getattr(
                        external, "description", None
                    ),  # Page description (extracted but not used to save space)
                }
                # ContentProcessor formats this as: "🔗 {title}: {uri}"
                # Note: Description is omitted to keep within Mastodon's character limits

            # === IMAGE ATTACHMENTS ===
            # Handle posts with one or more attached images
            # Each image can have alt text for accessibility
            # NOTE: Images can be direct OR nested in recordWithMedia (quote + images)
            images_to_process = []

            # Check for direct images first
            if hasattr(embed, "images") and embed.images:
                images_to_process = embed.images
            # Check for recordWithMedia (quoted post with images)
            elif hasattr(embed, "media") and embed.media:
                if hasattr(embed.media, "images") and embed.media.images:
                    images_to_process = embed.media.images
                    logger.debug(
                        "Found images in recordWithMedia embed (quoted post with images)"
                    )

            if images_to_process:
                images_data = []
                for image in images_to_process:
                    # Extract image metadata and accessibility info
                    image_data = {
                        "alt": getattr(
                            image, "alt", None
                        ),  # Alt text for screen readers
                        "aspect_ratio": getattr(
                            image, "aspect_ratio", None
                        ),  # Width:height ratio
                    }
                    # Additional blob/file metadata if available
                    if hasattr(image, "image") and image.image:
                        image_data["image"] = {
                            "mime_type": getattr(
                                image.image, "mime_type", None
                            ),  # e.g., "image/jpeg"
                            "size": getattr(
                                image.image, "size", None
                            ),  # File size in bytes
                        }
                        # Extract blob reference for downloading the image
                        if hasattr(image.image, "ref"):
                            # Convert AT Protocol blob reference to dict
                            ref = image.image.ref
                            if hasattr(ref, "link"):
                                image_data["image"]["ref"] = {"$link": ref.link}
                            elif hasattr(ref, "$link"):
                                image_data["image"]["ref"] = {"$link": ref["$link"]}
                            else:
                                # Try to extract as dict
                                image_data["image"]["ref"] = ref
                    images_data.append(image_data)
                embed_dict["images"] = images_data
                # ContentProcessor will format as: "📷 [N images]\nAlt text: ..."

            # === VIDEO ATTACHMENTS ===
            # Handle posts with video attachments
            if hasattr(embed, "video") and embed.video:
                video = embed.video
                embed_dict["video"] = {
                    "alt": getattr(embed, "alt", None),
                    "aspect_ratio": getattr(embed, "aspect_ratio", None),
                }
                # Extract video blob metadata
                if hasattr(video, "ref") and video.ref:
                    # Handle blob reference formats
                    ref = video.ref
                    if hasattr(ref, "link"):
                        embed_dict["video"]["blob_ref"] = ref.link
                    elif isinstance(ref, dict) and "$link" in ref:
                        embed_dict["video"]["blob_ref"] = ref["$link"]
                    else:
                        embed_dict["video"]["blob_ref"] = str(ref)

                    embed_dict["video"]["mime_type"] = getattr(
                        video, "mime_type", "video/mp4"
                    )
                    embed_dict["video"]["size"] = getattr(video, "size", 0)

                logger.debug("Found video embed with blob reference")

            # === QUOTED POSTS (Record Embeds) ===
            # Handle when users quote-tweet/quote-post another post
            # Currently basic implementation - could be expanded for full quote handling
            if hasattr(embed, "record") and embed.record:
                # TODO: Could extract quoted post author, text, etc. for richer display
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

    def download_video(self, blob_ref: str, did: str) -> Optional[Tuple[bytes, str]]:
        """Download video blob from AT Protocol

        Args:
            blob_ref: The blob reference hash
            did: User's DID for blob access

        Returns:
            Tuple of (video_bytes, mime_type) or None if download fails

        Note:
            Video files can be large (up to 50MB in AT Protocol).
            This method uses a 60-second timeout (vs 30s for images).
        """
        if not self._authenticated:
            logger.error("Client not authenticated")
            return None

        try:
            # Use the same blob download mechanism as images, but with longer timeout
            url = "https://bsky.social/xrpc/com.atproto.sync.getBlob"
            params = {"did": did, "cid": blob_ref}

            headers = {"User-Agent": "Social-Sync/1.0 (AT Protocol video downloader)"}

            # Add authentication if available
            if hasattr(self.client, "access_token") and self.client.access_token:
                headers["Authorization"] = f"Bearer {self.client.access_token}"

            response = requests.get(url, params=params, headers=headers, timeout=60)
            response.raise_for_status()

            # Get mime type from response headers (use lowercase for consistency)
            mime_type = response.headers.get("content-type", "video/mp4")
            video_bytes = response.content

            logger.info(f"Downloaded video blob: {len(video_bytes)} bytes")
            return (video_bytes, mime_type)

        except Exception as e:
            logger.error(f"Failed to download video blob {blob_ref}: {e}")
            return None
