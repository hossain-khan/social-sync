"""
Tests for Content Processor
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.content_processor import ContentProcessor


class TestContentProcessor:
    """Test suite for ContentProcessor class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = ContentProcessor()

    def test_truncate_if_needed_short_text(self):
        """Test that short text is not truncated"""
        text = "Short text"
        result = ContentProcessor._truncate_if_needed(text)
        assert result == text
        assert len(result) <= 500

    def test_truncate_if_needed_long_text(self):
        """Test that long text is properly truncated"""
        # Create text longer than 500 characters
        long_text = "x" * 600
        result = ContentProcessor._truncate_if_needed(long_text)

        assert len(result) <= 500
        assert result.endswith("...")
        # Should truncate to 497 chars plus "..." = 500 total
        assert len(result) == 500

    def test_truncate_if_needed_exactly_500_chars(self):
        """Test text exactly at the limit"""
        text = "x" * 500
        result = ContentProcessor._truncate_if_needed(text)
        assert result == text
        assert len(result) == 500

    def test_extract_hashtags_simple(self):
        """Test extracting hashtags from text"""
        processor = ContentProcessor()
        text = "Check out these #test #hashtags"

        result = processor.extract_hashtags(text)

        # Returns hashtags without # prefix
        assert result == ["test", "hashtags"]

    def test_extract_hashtags_no_hashtags(self):
        """Test hashtag extraction with no hashtags"""
        text = "This text has no hashtags"
        result = ContentProcessor.extract_hashtags(text)
        assert result == []

    def test_extract_hashtags_mixed_case(self):
        """Test hashtag extraction with mixed case"""
        text = "Testing #HashTag and #lowercase"
        result = ContentProcessor.extract_hashtags(text)
        assert result == ["HashTag", "lowercase"]

    def test_extract_mentions_simple(self):
        """Test mention extraction from simple text"""
        text = "Hello @john and @jane.doe"
        result = ContentProcessor.extract_mentions(text)
        # Returns mentions without @ prefix
        assert result == ["john", "jane.doe"]

    def test_extract_mentions_no_mentions(self):
        """Test mention extraction with no mentions"""
        text = "This text has no mentions"
        result = ContentProcessor.extract_mentions(text)
        assert result == []

    def test_extract_urls_simple(self):
        """Test URL extraction from simple text"""
        text = "Check out https://example.com and http://test.org"
        result = ContentProcessor.extract_urls(text)
        assert "https://example.com" in result
        assert "http://test.org" in result

    def test_extract_urls_no_urls(self):
        """Test URL extraction with no URLs"""
        text = "This text has no URLs"
        result = ContentProcessor.extract_urls(text)
        assert result == []

    def test_add_sync_attribution_default(self):
        """Test adding sync attribution with default source"""
        text = "Original post content"
        result = ContentProcessor.add_sync_attribution(text)
        assert result == "Original post content\n\n(via Bluesky 🦋)"

    def test_add_sync_attribution_custom_source(self):
        """Test adding sync attribution with custom source"""
        text = "Original post content"
        result = ContentProcessor.add_sync_attribution(text, "Twitter")
        assert result == "Original post content\n\n(via Twitter)"

    def test_add_sync_attribution_empty_text(self):
        """Test adding sync attribution to empty text"""
        text = ""
        result = ContentProcessor.add_sync_attribution(text)
        assert result == "\n\n(via Bluesky 🦋)"

    def test_convert_mentions_at_protocol(self):
        """Test converting AT Protocol mentions"""
        text = "Hello @user.bsky.social and @another.handle"
        result = ContentProcessor._convert_mentions(text)
        # Should preserve the mentions as-is
        assert "@user.bsky.social" in result
        assert "@another.handle" in result

    def test_expand_urls_from_facets_empty_facets(self):
        """Test URL expansion with empty facets"""
        text = "Simple text"
        facets = []
        result = ContentProcessor._expand_urls_from_facets(text, facets)
        assert result == text

    def test_expand_urls_from_facets_with_links(self):
        """Test URL expansion with link facets"""
        text = "Check this out!"
        facets = [
            {
                "index": {"byteStart": 0, "byteEnd": 15},
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": "https://example.com",
                    }
                ],
            }
        ]
        result = ContentProcessor._expand_urls_from_facets(text, facets)
        assert "https://example.com" in result

    def test_extract_images_from_embed_no_embed(self):
        """Test image extraction with no embed"""
        result = ContentProcessor.extract_images_from_embed(None)
        assert result == []

    def test_extract_images_from_embed_no_images(self):
        """Test image extraction with non-image embed"""
        embed = {
            "$type": "app.bsky.embed.external",
            "external": {"uri": "https://example.com", "title": "Example Site"},
        }
        result = ContentProcessor.extract_images_from_embed(embed)
        assert result == []

    def test_extract_images_from_embed_single_image(self):
        """Test image extraction with single image embed"""
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "alt": "Test image",
                    "image": {
                        "$type": "blob",
                        "ref": {"$link": "test-blob-ref"},
                        "mimeType": "image/jpeg",
                        "size": 123456,
                    },
                }
            ],
        }
        result = ContentProcessor.extract_images_from_embed(embed)
        assert len(result) == 1
        assert result[0]["alt"] == "Test image"
        assert result[0]["blob_ref"] == "test-blob-ref"
        assert result[0]["mime_type"] == "image/jpeg"

    def test_extract_images_from_embed_multiple_images(self):
        """Test image extraction with multiple image embed"""
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "alt": "First image",
                    "image": {
                        "$type": "blob",
                        "ref": {"$link": "blob-ref-1"},
                        "mimeType": "image/jpeg",
                    },
                },
                {
                    "alt": "Second image",
                    "image": {
                        "$type": "blob",
                        "ref": {"$link": "blob-ref-2"},
                        "mimeType": "image/png",
                    },
                },
            ],
        }
        result = ContentProcessor.extract_images_from_embed(embed)
        assert len(result) == 2
        assert result[0]["alt"] == "First image"
        assert result[1]["alt"] == "Second image"

    def test_extract_images_from_embed_record_with_media(self):
        """Test image extraction from recordWithMedia embed (quoted post with images)"""
        # This tests the fix for quoted posts with images not syncing
        embed = {
            "py_type": "app.bsky.embed.recordWithMedia",
            "images": [
                {
                    "alt": "Image from quoted post",
                    "image": {
                        "$type": "blob",
                        "ref": {
                            "$link": "bafkreiett2bw6haj672k7l6gk32dwqdd27j3ks6hgsokhxkgyixr4we77i"
                        },
                        "mimeType": "image/jpeg",
                        "size": 600344,
                    },
                },
                {
                    "alt": "",
                    "image": {
                        "$type": "blob",
                        "ref": {
                            "$link": "bafkreignydqmw2pqgm7jo3g4jnuu6ztr53fy26llwoul2gtkd6n7xkvvce"
                        },
                        "mimeType": "image/jpeg",
                        "size": 730298,
                    },
                },
            ],
            "record": {"py_type": "app.bsky.embed.record"},
        }
        result = ContentProcessor.extract_images_from_embed(embed)
        assert len(result) == 2, "Should extract images from recordWithMedia embed"
        assert result[0]["alt"] == "Image from quoted post"
        assert (
            result[0]["blob_ref"]
            == "bafkreiett2bw6haj672k7l6gk32dwqdd27j3ks6hgsokhxkgyixr4we77i"
        )
        assert result[0]["mime_type"] == "image/jpeg"
        assert result[1]["alt"] == ""
        assert (
            result[1]["blob_ref"]
            == "bafkreignydqmw2pqgm7jo3g4jnuu6ztr53fy26llwoul2gtkd6n7xkvvce"
        )
        assert result[1]["mime_type"] == "image/jpeg"

    @patch("src.content_processor.requests.get")
    def test_download_image_success(self, mock_get):
        """Test successful image download"""
        # Use spec to make mock more restrictive and catch attribute errors
        mock_response = Mock(spec=["content", "headers", "raise_for_status"])
        mock_response.content = b"fake_image_data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status.return_value = None  # Successful status check
        mock_get.return_value = mock_response

        result = ContentProcessor.download_image("https://example.com/image.jpg")
        assert result is not None
        content, mime_type = result
        assert content == b"fake_image_data"
        assert mime_type == "image/jpeg"

    @patch("src.content_processor.requests.get")
    def test_download_image_failure(self, mock_get):
        """Test failed image download"""
        mock_get.side_effect = Exception("Network error")

        result = ContentProcessor.download_image("https://example.com/image.jpg")
        assert result is None

    @patch("src.content_processor.requests.get")
    def test_download_image_http_error(self, mock_get):
        """Test HTTP error during image download"""
        mock_response = Mock(spec=["raise_for_status"])
        mock_response.raise_for_status.side_effect = Exception("HTTP 404 Not Found")
        mock_get.return_value = mock_response

        result = ContentProcessor.download_image("https://example.com/image.jpg")
        assert result is None

    @patch("src.content_processor.requests.get")
    def test_download_image_missing_content_type(self, mock_get):
        """Test image download with missing content-type header"""
        mock_response = Mock(spec=["content", "headers", "raise_for_status"])
        mock_response.content = b"fake_image_data"
        mock_response.headers = {}  # Missing content-type
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = ContentProcessor.download_image("https://example.com/image.jpg")
        assert result is not None
        content, mime_type = result
        assert content == b"fake_image_data"
        assert mime_type == "image/jpeg"  # Default MIME type when missing

    def test_process_bluesky_to_mastodon_simple_text(self):
        """Test processing simple text post"""
        result = self.processor.process_bluesky_to_mastodon(
            text="Simple test post", embed=None, facets=[]
        )
        assert result == "Simple test post"

    def test_process_bluesky_to_mastodon_with_hashtags_and_mentions(self):
        """Test processing post with hashtags and mentions"""
        text = "Hello @user this is a #test"
        facets = []  # Simplified for this test

        result = self.processor.process_bluesky_to_mastodon(
            text=text, embed=None, facets=facets
        )
        assert "#test" in result
        assert "@user" in result

    def test_process_bluesky_to_mastodon_long_text(self):
        """Test processing text that exceeds character limit"""
        long_text = "x" * 600

        result = self.processor.process_bluesky_to_mastodon(
            text=long_text, embed=None, facets=[]
        )
        assert len(result) <= 500
        assert result.endswith("...")

    def test_handle_embed_external_link(self):
        """Test handling external link embed"""
        embed = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": "https://example.com",
                "title": "Example Site",
                "description": "A test site",
            },
        }

        result = ContentProcessor._handle_embed(
            "Original text", embed, include_image_placeholders=True
        )
        assert "🔗 Example Site" in result
        assert "https://example.com" in result
        # Note: Description is intentionally not included to keep within character limits

    def test_handle_embed_images_with_placeholders(self):
        """Test handling image embed with placeholders"""
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [{"alt": "Test image"}, {"alt": "Another image"}],
        }

        result = ContentProcessor._handle_embed(
            "Original text", embed, include_image_placeholders=True
        )
        assert "📷 [2 images]" in result
        assert "Test image" in result
        assert "Another image" in result

    def test_handle_embed_images_without_placeholders(self):
        """Test handling image embed without placeholders"""
        embed = {
            "$type": "app.bsky.embed.images",
            "images": [{"alt": "Test image"}, {"alt": "Another image"}],
        }

        result = ContentProcessor._handle_embed(
            "Original text", embed, include_image_placeholders=False
        )
        # Should return original text when not including placeholders
        assert result == "Original text"

    def test_handle_embed_quote_post(self):
        """Test handling quoted post embed"""
        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Original quoted post"},
                "author": {"handle": "user.bsky.social", "displayName": "Test User"},
            },
        }

        result = ContentProcessor._handle_embed(
            "Original text", embed, include_image_placeholders=True
        )
        assert "Quoting @user.bsky.social" in result
        assert "Original quoted post" in result

    def test_handle_embed_unsupported_type(self):
        """Test handling unsupported embed type"""
        embed = {"$type": "app.bsky.embed.unknown", "data": "some data"}

        result = ContentProcessor._handle_embed(
            "Original text", embed, include_image_placeholders=True
        )
        assert result == "Original text"

    def test_no_duplicate_links_with_facets_and_embed(self):
        """Test that links don't get duplicated when both facets and external embed exist"""
        text = "Check out this site: https://keepachangelog.com..."

        # Facets that should expand the truncated URL
        facets = [
            {
                "index": {"byteStart": 21, "byteEnd": 49},
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": "https://keepachangelog.com/en/1.0.0/",
                    }
                ],
            }
        ]

        # No external embed - this is the key difference from the bug scenario
        embed = None

        result = ContentProcessor.process_bluesky_to_mastodon(
            text=text, embed=embed, facets=facets, include_image_placeholders=True
        )

        # Should have the full URL expanded, no duplicates
        assert "https://keepachangelog.com/en/1.0.0/" in result
        # Should not have the truncated URL anymore
        assert "https://keepachangelog.com..." not in result
        # Should only appear once
        assert result.count("https://keepachangelog.com") == 1

    def test_duplicate_link_bug_scenario(self):
        """Test the specific scenario that caused the duplicate link bug"""
        text = "TIL: There is a nice site with guideline on how to author changelogs. ❤️\nhttps://keepachangelog.com..."

        # Facets that should expand the truncated URL
        facets = [
            {
                "index": {"byteStart": 77, "byteEnd": 106},
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": "https://keepachangelog.com/en/1.0.0/",
                    }
                ],
            }
        ]

        # No external embed in this case
        embed = None

        result = ContentProcessor.process_bluesky_to_mastodon(
            text=text, embed=embed, facets=facets, include_image_placeholders=True
        )

        # Should have the full URL expanded, no truncated URL
        assert "https://keepachangelog.com/en/1.0.0/" in result
        assert "https://keepachangelog.com..." not in result
        # Should only appear once total
        link_count = result.count("https://keepachangelog.com")
        assert link_count == 1, f"Expected 1 link, found {link_count} in: {result}"

    def test_duplicate_link_with_facets_and_external_embed(self):
        """Test that we don't duplicate links when both facets and external embed exist"""
        text = "Check out this site: https://keepachangelog.com..."

        # Facets that expand the URL in the text
        facets = [
            {
                "index": {"byteStart": 21, "byteEnd": 49},
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": "https://keepachangelog.com/en/1.0.0/",
                    }
                ],
            }
        ]

        # AND an external embed for the same URL - this could cause duplication
        embed = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": "https://keepachangelog.com/en/1.0.0/",
                "title": "Keep a Changelog",
                "description": "Don't let your friends dump git logs into changelogs.",
            },
        }

        result = ContentProcessor.process_bluesky_to_mastodon(
            text=text, embed=embed, facets=facets, include_image_placeholders=True
        )

        # Should only have the link appear once, not duplicated
        # The facets should expand the truncated URL, but we shouldn't add it again via external embed
        link_count = result.count("https://keepachangelog.com")
        assert link_count == 1, f"Expected 1 link, found {link_count} in: {result}"

        # Should have the full URL, not the truncated version
        assert "https://keepachangelog.com/en/1.0.0/" in result
        assert "https://keepachangelog.com..." not in result

    def test_external_embed_only_no_facets(self):
        """Test external embed works correctly when there are no facets (normal case)"""
        text = "Check out this cool library!"

        # No facets - just an external embed
        facets = None

        # External embed with title and link
        embed = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": "https://github.com/example/awesome-lib",
                "title": "Awesome Library",
                "description": "A really cool library for developers",
            },
        }

        result = ContentProcessor.process_bluesky_to_mastodon(
            text=text, embed=embed, facets=facets, include_image_placeholders=True
        )

        # Should have the original text plus the external link
        assert "Check out this cool library!" in result
        assert "🔗 Awesome Library: https://github.com/example/awesome-lib" in result
        # Should only appear once
        link_count = result.count("https://github.com/example/awesome-lib")
        assert link_count == 1, f"Expected 1 link, found {link_count} in: {result}"

    def test_has_no_sync_tag_true(self):
        """Test detecting #no-sync tag in text"""
        text = "This is a test post #no-sync"
        assert ContentProcessor.has_no_sync_tag(text) is True

    def test_has_no_sync_tag_false(self):
        """Test that posts without #no-sync tag return False"""
        text = "This is a test post #other #tags"
        assert ContentProcessor.has_no_sync_tag(text) is False

    def test_has_no_sync_tag_empty_text(self):
        """Test empty text returns False"""
        assert ContentProcessor.has_no_sync_tag("") is False
        assert ContentProcessor.has_no_sync_tag(None) is False

    def test_has_no_sync_tag_case_insensitive(self):
        """Test that #no-sync tag detection is case-insensitive"""
        assert ContentProcessor.has_no_sync_tag("Test #no-sync") is True
        assert ContentProcessor.has_no_sync_tag("Test #No-Sync") is True
        assert ContentProcessor.has_no_sync_tag("Test #NO-SYNC") is True
        assert ContentProcessor.has_no_sync_tag("Test #No-sync") is True

    def test_has_no_sync_tag_with_other_tags(self):
        """Test detecting #no-sync among other hashtags"""
        text = "Check out #python #no-sync #development #tutorial"
        assert ContentProcessor.has_no_sync_tag(text) is True

    def test_has_no_sync_tag_middle_of_text(self):
        """Test detecting #no-sync tag in middle of text"""
        text = "This is #no-sync a test post"
        assert ContentProcessor.has_no_sync_tag(text) is True

    def test_has_no_sync_tag_multiple_occurrences(self):
        """Test detecting #no-sync when it appears multiple times"""
        text = "Testing #no-sync multiple #no-sync times"
        assert ContentProcessor.has_no_sync_tag(text) is True

    def test_has_no_sync_tag_partial_match_false(self):
        """Test that partial matches don't trigger the filter"""
        # These should NOT be detected as no-sync
        assert ContentProcessor.has_no_sync_tag("Test #no-synchronization") is False
        assert ContentProcessor.has_no_sync_tag("Test #nosync") is False
        assert ContentProcessor.has_no_sync_tag("Test #no-sync-please") is False
