"""
Content processing utilities for Social Sync
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Processes content for cross-platform compatibility"""

    # Mastodon character limit
    MASTODON_CHAR_LIMIT = 500

    # AT Protocol/Bluesky facets patterns
    MENTION_PATTERN = re.compile(r"@([a-zA-Z0-9.-]+\.?[a-zA-Z]{2,})")
    HASHTAG_PATTERN = re.compile(r"#([^\s#]+)")
    URL_PATTERN = re.compile(r"https?://[^\s]+")

    @staticmethod
    def process_bluesky_to_mastodon(
        text: str,
        embed: Optional[Dict[str, Any]] = None,
        include_image_placeholders: bool = True,
    ) -> str:
        """
        Process Bluesky post content for Mastodon compatibility

        Args:
            text: The original post text
            embed: Embed data from Bluesky
            include_image_placeholders: Whether to add text placeholders for images
        """
        processed_text = text

        # Handle embedded content
        if embed:
            processed_text = ContentProcessor._handle_embed(
                processed_text, embed, include_image_placeholders
            )

        # Convert AT Protocol mentions to Mastodon format if possible
        # Note: This is a basic conversion - full handle resolution would require more work
        processed_text = ContentProcessor._convert_mentions(processed_text)

        # Ensure we stay within Mastodon's character limit
        processed_text = ContentProcessor._truncate_if_needed(processed_text)

        return processed_text

    @staticmethod
    def _handle_embed(
        text: str, embed: Dict[str, Any], include_image_placeholders: bool = True
    ) -> str:
        """Handle embedded content from Bluesky posts"""
        embed_type = (
            embed.get("py_type", "").split(".")[-1] if embed.get("py_type") else ""
        )

        if embed_type == "External":
            # Handle external links
            external = embed.get("external", {})
            if external.get("uri"):
                link_text = f"\n\n🔗 {external.get('title', 'Link')}: {external['uri']}"
                if external.get("description"):
                    link_text += f"\n{external['description']}"
                return text + link_text

        elif embed_type == "Images":
            # Handle images
            images = embed.get("images", [])
            if images and include_image_placeholders:
                image_count = len(images)
                image_text = (
                    f"\n\n📷 [{image_count} image{'s' if image_count > 1 else ''}]"
                )

                # Add alt text if available
                alt_texts = []
                for img in images:
                    if img.get("alt"):
                        alt_texts.append(img["alt"])

                if alt_texts:
                    image_text += f"\nAlt text: {' | '.join(alt_texts)}"

                return text + image_text

        elif embed_type == "Record":
            # Handle quoted posts/records
            record = embed.get("record", {})
            if record.get("py_type", "").endswith("ViewRecord"):
                author = record.get("author", {})
                quote_text = record.get("value", {}).get("text", "")
                if author.get("handle") and quote_text:
                    quote_preview = (
                        quote_text[:100] + "..."
                        if len(quote_text) > 100
                        else quote_text
                    )
                    return text + f"\n\nQuoting @{author['handle']}:\n> {quote_preview}"

        return text

    @staticmethod
    def _convert_mentions(text: str) -> str:
        """Convert AT Protocol mentions to a more generic format"""
        # For now, just keep mentions as-is
        # In a more sophisticated version, we could resolve handles to Mastodon usernames
        return text

    @staticmethod
    def _truncate_if_needed(text: str) -> str:
        """Truncate text if it exceeds Mastodon's character limit"""
        if len(text) <= ContentProcessor.MASTODON_CHAR_LIMIT:
            return text

        # Try to truncate at a word boundary
        truncated = text[: ContentProcessor.MASTODON_CHAR_LIMIT - 3]
        last_space = truncated.rfind(" ")

        if (
            last_space > ContentProcessor.MASTODON_CHAR_LIMIT * 0.8
        ):  # If we can save at least 20% by truncating at word boundary
            truncated = truncated[:last_space]

        return truncated + "..."

    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Extract hashtags from text"""
        return ContentProcessor.HASHTAG_PATTERN.findall(text)

    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """Extract mentions from text"""
        return ContentProcessor.MENTION_PATTERN.findall(text)

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text"""
        return ContentProcessor.URL_PATTERN.findall(text)

    @staticmethod
    def add_sync_attribution(text: str, source: str = "Bluesky") -> str:
        """Add attribution that content was synced from another platform"""
        # Only add attribution if there's room and it's not already present
        # Add butterfly emoji for Bluesky attribution
        attribution = (
            f"\n\n(via {source} 🦋)" if source == "Bluesky" else f"\n\n(via {source})"
        )

        if (
            "(via" not in text
            and len(text + attribution) <= ContentProcessor.MASTODON_CHAR_LIMIT
        ):
            return text + attribution

        return text

    @staticmethod
    def extract_images_from_embed(embed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract image information from Bluesky embed data

        Returns a list of image dictionaries with 'url', 'alt', and 'mime_type' keys
        """
        images: List[Dict[str, Any]] = []

        if not embed:
            return images

        embed_type = (
            embed.get("py_type", "").split(".")[-1] if embed.get("py_type") else ""
        )

        if embed_type == "Images":
            bluesky_images = embed.get("images", [])
            for img in bluesky_images:
                # Extract image URL and metadata
                image_info = {"url": None, "alt": img.get("alt", ""), "mime_type": None}

                # Get image blob reference
                if img.get("image"):
                    blob = img["image"]
                    if isinstance(blob, dict):
                        image_info["mime_type"] = blob.get("mime_type", "image/jpeg")
                        # The blob ref contains the image identifier
                        if blob.get("ref"):
                            # For AT Protocol, we'll need to construct the blob URL
                            # This will be handled by a separate download method
                            image_info["blob_ref"] = blob["ref"]

                if image_info["url"] or image_info.get("blob_ref"):
                    images.append(image_info)

        return images

    @staticmethod
    def download_image(image_url: str) -> Optional[Tuple[bytes, str]]:
        """Download image from URL

        Returns tuple of (image_bytes, mime_type) or None if failed
        """
        try:
            headers = {"User-Agent": "Social-Sync/1.0 (Image sync bot)"}
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Get mime type from response or guess from URL
            mime_type = response.headers.get("content-type", "image/jpeg")
            if not mime_type.startswith("image/"):
                mime_type = "image/jpeg"

            return response.content, mime_type

        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            return None
