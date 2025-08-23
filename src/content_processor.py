"""
Content processing utilities for Social Sync
"""

import logging
import re
from typing import Any, Dict, List, Optional

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
        text: str, embed: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process Bluesky post content for Mastodon compatibility
        """
        processed_text = text

        # Handle embedded content
        if embed:
            processed_text = ContentProcessor._handle_embed(processed_text, embed)

        # Convert AT Protocol mentions to Mastodon format if possible
        # Note: This is a basic conversion - full handle resolution would require more work
        processed_text = ContentProcessor._convert_mentions(processed_text)

        # Ensure we stay within Mastodon's character limit
        processed_text = ContentProcessor._truncate_if_needed(processed_text)

        return processed_text

    @staticmethod
    def _handle_embed(text: str, embed: Dict[str, Any]) -> str:
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
            if images:
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
        attribution = f"\n\n(via {source})"

        if (
            "(via" not in text
            and len(text + attribution) <= ContentProcessor.MASTODON_CHAR_LIMIT
        ):
            return text + attribution

        return text
