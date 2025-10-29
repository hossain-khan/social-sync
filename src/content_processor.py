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
    MENTION_PATTERN = re.compile(r"@([a-zA-Z0-9][a-zA-Z0-9.-]*\.?[a-zA-Z]{2,})")
    URL_PATTERN = re.compile(r"https?://[^\s]+")
    # Note: HASHTAG extraction uses custom logic in extract_hashtags() method
    # due to complex edge cases that can't be handled by a single regex

    @staticmethod
    def process_bluesky_to_mastodon(
        text: str,
        embed: Optional[Dict[str, Any]] = None,
        facets: Optional[List[Dict[str, Any]]] = None,
        include_image_placeholders: bool = True,
        include_sync_attribution: bool = False,
    ) -> str:
        """
        Process Bluesky post content for Mastodon compatibility

        Args:
            text: The original post text
            embed: Embed data from Bluesky
            facets: Facets data containing rich text annotations (URLs, mentions, etc.)
            include_image_placeholders: Whether to add text placeholders for images
            include_sync_attribution: Whether to add "(via Bluesky 🦋)" attribution
        """
        processed_text = text

        # First expand URLs using facets
        if facets:
            processed_text = ContentProcessor._expand_urls_from_facets(
                processed_text, facets
            )

        # Handle embedded content
        if embed:
            processed_text = ContentProcessor._handle_embed(
                processed_text, embed, include_image_placeholders
            )

        # Convert AT Protocol mentions to Mastodon format if possible
        # Note: This is a basic conversion - full handle resolution would require more work
        processed_text = ContentProcessor._convert_mentions(processed_text)

        # Add sync attribution before truncation if requested
        if include_sync_attribution:
            processed_text = ContentProcessor.add_sync_attribution(processed_text)

        # Ensure we stay within Mastodon's character limit
        processed_text = ContentProcessor._truncate_if_needed(processed_text)

        return processed_text

    @staticmethod
    def _expand_urls_from_facets(text: str, facets: List[Dict[str, Any]]) -> str:
        """Expand truncated URLs using facets data from Bluesky

        Properly handles multi-byte UTF-8 characters in byte position calculations.
        Facets contain the full URL information that corresponds to
        truncated URLs in the post text.
        """
        if not facets:
            return text

        # Convert text to bytes for accurate indexing
        text_bytes = text.encode("utf-8")

        # Process facets in reverse order to avoid index shifting when replacing text
        sorted_facets = sorted(
            facets, key=lambda f: f.get("index", {}).get("byteStart", 0), reverse=True
        )

        for facet in sorted_facets:
            try:
                # Get the byte range for this facet
                facet_index = facet.get("index", {})
                byte_start = facet_index.get("byteStart")
                byte_end = facet_index.get("byteEnd")

                if byte_start is None or byte_end is None:
                    continue

                # Look for link features in this facet
                features = facet.get("features", [])
                for feature in features:
                    # Check if this is a link feature
                    # AT Protocol uses $type, but atproto SDK might convert to py_type
                    feature_type = feature.get("$type", "") or feature.get(
                        "py_type", ""
                    )
                    if (
                        feature_type.endswith("Link")
                        or feature_type == "app.bsky.richtext.facet#link"
                    ):
                        full_url = feature.get("uri")
                        if full_url:
                            # Replace at byte positions
                            if byte_end <= len(text_bytes):
                                text_bytes = (
                                    text_bytes[:byte_start]
                                    + full_url.encode("utf-8")
                                    + text_bytes[byte_end:]
                                )
                                logger.debug(f"Expanded URL from facets: {full_url}")
                            break

            except Exception as e:
                logger.warning(f"Error processing facet for URL expansion: {e}")
                continue

        # Decode back to string
        return text_bytes.decode("utf-8", errors="replace")

    @staticmethod
    def _handle_embed(
        text: str, embed: Dict[str, Any], include_image_placeholders: bool = True
    ) -> str:
        """Handle embedded content from Bluesky posts"""
        embed_type = (
            embed.get("py_type", "").split(".")[-1]
            if embed.get("py_type")
            else embed.get("$type", "").split(".")[-1] if embed.get("$type") else ""
        )

        if embed_type == "external":
            # Handle external links - keep concise to avoid Mastodon character limits
            external = embed.get("external", {})
            if external.get("uri"):
                # Check if this URL is already present in the text (from facets expansion)
                # to avoid duplicate links
                external_uri = external["uri"]
                if external_uri not in text:
                    link_text = (
                        f"\n\n🔗 {external.get('title', 'Link')}: {external_uri}"
                    )
                    # Note: Deliberately not including description to keep posts within character limits
                    return text + link_text
                else:
                    # URL already in text (likely from facets), don't add again
                    logger.debug(f"Skipping duplicate external link: {external_uri}")
                    return text

        elif embed_type == "images":
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

        elif embed_type == "record":
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
        # Strategy: find all hashtag-like patterns, then filter based on context
        hashtags = []

        # Use the original simple pattern
        original_pattern = re.compile(r"#([^\s#]+)")

        # First, find all hashtag positions that should be excluded
        excluded_positions = set()

        # Exclude hashtags that start with ##
        double_hash_pattern = re.compile(r"##[^\s#]+")
        for match in double_hash_pattern.finditer(text):
            # Mark both # positions as excluded
            excluded_positions.add(match.start())
            excluded_positions.add(match.start() + 1)

        # Now find valid hashtags
        for match in original_pattern.finditer(text):
            start_pos = match.start()
            hashtag_content = match.group(1)

            # Skip if this position was marked as excluded
            if start_pos in excluded_positions:
                continue

            # Skip if # is in middle of non-hashtag word
            if start_pos > 0:
                prev_char = text[start_pos - 1]
                # Allow if previous char is not alphanumeric (space, punctuation, etc)
                # OR if we're in a hashtag context (will be handled by position tracking)
                if prev_char.isalnum():
                    # Check if this looks like middle of a word (not hashtag boundary)
                    # Look backwards to see if this could be start of new hashtag

                    # Find start of the word this # is in
                    word_start = start_pos - 1
                    while word_start > 0 and text[word_start - 1].isalnum():
                        word_start -= 1

                    # If the word doesn't start with #, then this # is in middle of word
                    if word_start == 0 or text[word_start - 1] != "#":
                        continue

            hashtags.append(hashtag_content)

        return hashtags

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
            embed.get("py_type", "").split(".")[-1]
            if embed.get("py_type")
            else embed.get("$type", "").split(".")[-1] if embed.get("$type") else ""
        )

        # Extract images if present - can be in "images" embed type OR in recordWithMedia
        # recordWithMedia = quoted post + images (images stored in same "images" field)
        if embed_type == "images" or (
            embed_type == "recordWithMedia" and embed.get("images")
        ):
            bluesky_images = embed.get("images", [])
            for img in bluesky_images:
                # Extract image URL and metadata
                # Handle both dict and AT Protocol Image objects
                if hasattr(img, "alt"):
                    # AT Protocol Image object
                    alt_text = img.alt or ""
                    blob = img.image if hasattr(img, "image") else None
                else:
                    # Dict format
                    alt_text = img.get("alt", "")
                    blob = img.get("image")

                image_info = {"url": None, "alt": alt_text, "mime_type": None}

                # Get image blob reference
                if blob:
                    if hasattr(blob, "mime_type"):
                        # AT Protocol BlobRef object
                        image_info["mime_type"] = blob.mime_type
                        if hasattr(blob, "ref") and hasattr(blob.ref, "link"):
                            image_info["blob_ref"] = blob.ref.link
                    elif isinstance(blob, dict):
                        # Dict format
                        image_info["mime_type"] = blob.get("mime_type", "image/jpeg")
                        # The blob ref contains the image identifier
                        if blob.get("ref"):
                            # For AT Protocol, we'll need to construct the blob URL
                            # This will be handled by a separate download method
                            ref = blob["ref"]
                            if isinstance(ref, dict) and "$link" in ref:
                                image_info["blob_ref"] = ref["$link"]
                            else:
                                image_info["blob_ref"] = ref

                if image_info["url"] or image_info.get("blob_ref"):
                    images.append(image_info)

        return images

    @staticmethod
    def has_no_sync_tag(text: str) -> bool:
        """Check if text contains the #no-sync tag

        Args:
            text: The text to check for the #no-sync tag

        Returns:
            True if the text contains #no-sync tag, False otherwise
        """
        if not text:
            return False

        # Extract all hashtags from the text
        hashtags = ContentProcessor.extract_hashtags(text)

        # Check if 'no-sync' is in the hashtags (case-insensitive)
        return any(tag.lower() == "no-sync" for tag in hashtags)

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
