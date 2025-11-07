"""
Tests for quote depth limiting and circular reference detection in ContentProcessor
"""

import sys
from pathlib import Path

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.content_processor import ContentProcessor


class TestQuoteDepthLimiting:
    """Test suite for quote depth limiting functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = ContentProcessor()

    def test_quote_depth_limiting_depth_1(self):
        """Test that quotes at depth 1 are processed normally"""
        # Post A quotes Post B
        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/quotedpost",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "This is the quoted post content"},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Post A content", embed=embed
        )

        assert "Quoting @user.bsky.social" in result
        assert "This is the quoted post content" in result
        assert "[Additional quoted content omitted" not in result

    def test_quote_depth_limiting_depth_2(self):
        """Test that quotes at depth 2 are processed normally"""
        # Post A quotes Post B, Post B quotes Post C
        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": "Post B content",
                    "embed": {
                        "$type": "app.bsky.embed.record",
                        "record": {
                            "uri": "at://did:plc:test/app.bsky.feed.post/postc",
                            "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                            "value": {"text": "Post C content"},
                            "author": {"handle": "userc.bsky.social"},
                        },
                    },
                },
                "author": {"handle": "userb.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Post A content", embed=embed
        )

        assert "Quoting @userb.bsky.social" in result
        assert "Post B content" in result
        assert "Quoting @userc.bsky.social" in result
        assert "Post C content" in result
        assert "[Additional quoted content omitted" not in result

    def test_quote_depth_limiting_depth_3_truncated(self):
        """Test that quotes at depth 3 are truncated with MAX_QUOTE_DEPTH=2"""
        # Post A quotes Post B, Post B quotes Post C, Post C quotes Post D
        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": "Post B content",
                    "embed": {
                        "$type": "app.bsky.embed.record",
                        "record": {
                            "uri": "at://did:plc:test/app.bsky.feed.post/postc",
                            "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                            "value": {
                                "text": "Post C content",
                                "embed": {
                                    "$type": "app.bsky.embed.record",
                                    "record": {
                                        "uri": "at://did:plc:test/app.bsky.feed.post/postd",
                                        "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                                        "value": {"text": "Post D content"},
                                        "author": {"handle": "userd.bsky.social"},
                                    },
                                },
                            },
                            "author": {"handle": "userc.bsky.social"},
                        },
                    },
                },
                "author": {"handle": "userb.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Post A content", embed=embed
        )

        # Should include A -> B -> C but not D
        assert "Quoting @userb.bsky.social" in result
        assert "Post B content" in result
        assert "Quoting @userc.bsky.social" in result
        assert "Post C content" in result

        # Post D should be truncated with warning message
        assert "userd.bsky.social" not in result
        assert "Post D content" not in result
        assert "[Additional quoted content omitted due to depth...]" in result

    def test_quote_depth_limiting_deep_nesting(self):
        """Test that deeply nested quotes (5 levels) are properly limited"""
        # Create a chain: A -> B -> C -> D -> E (5 levels)
        # Should only show A -> B -> C (depth 2)
        embed_e = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/poste",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Post E - level 5"},
                "author": {"handle": "usere.bsky.social"},
            },
        }

        embed_d = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postd",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Post D - level 4", "embed": embed_e},
                "author": {"handle": "userd.bsky.social"},
            },
        }

        embed_c = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postc",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Post C - level 3", "embed": embed_d},
                "author": {"handle": "userc.bsky.social"},
            },
        }

        embed_b = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Post B - level 2", "embed": embed_c},
                "author": {"handle": "userb.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Post A - level 1", embed=embed_b
        )

        # Should contain up to depth 2 (B and C)
        assert "Post A - level 1" in result
        assert "Quoting @userb.bsky.social" in result
        assert "Post B - level 2" in result
        assert "Quoting @userc.bsky.social" in result
        assert "Post C - level 3" in result

        # Should NOT contain D or E
        assert "userd.bsky.social" not in result
        assert "Post D - level 4" not in result
        assert "usere.bsky.social" not in result
        assert "Post E - level 5" not in result

        # Should have depth warning
        assert "[Additional quoted content omitted due to depth...]" in result


class TestCircularReferenceDetection:
    """Test suite for circular reference detection in quoted posts"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = ContentProcessor()

    def test_circular_reference_simple(self):
        """Test detection of simple circular reference (A quotes B, B quotes A)"""
        # This is a simplified test - in reality, you'd need to process
        # the embed structure that contains the circular reference
        # We'll test the seen_uris mechanism by calling _handle_embed directly

        # Simulate Post A quoting Post B, where Post B tries to quote Post A
        seen_uris = set()
        seen_uris.add("at://did:plc:test/app.bsky.feed.post/posta")

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/posta",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "This would create a circular reference"},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = ContentProcessor._handle_embed(
            "Original text",
            embed,
            include_image_placeholders=True,
            quote_depth=1,
            seen_uris=seen_uris,
        )

        # Should detect circular reference and add warning
        assert "[Circular quote reference detected]" in result
        assert "This would create a circular reference" not in result

    def test_no_circular_reference_different_uris(self):
        """Test that different URIs don't trigger circular detection"""
        seen_uris = set()
        seen_uris.add("at://did:plc:test/app.bsky.feed.post/posta")

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Different post, no circular reference"},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = ContentProcessor._handle_embed(
            "Original text",
            embed,
            include_image_placeholders=True,
            quote_depth=1,
            seen_uris=seen_uris,
        )

        # Should NOT detect circular reference
        assert "[Circular quote reference detected]" not in result
        assert "Different post, no circular reference" in result

    def test_circular_reference_empty_uri(self):
        """Test that empty URIs don't cause issues"""
        seen_uris = set()

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "",  # Empty URI
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Post with empty URI"},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = ContentProcessor._handle_embed(
            "Original text",
            embed,
            include_image_placeholders=True,
            quote_depth=1,
            seen_uris=seen_uris,
        )

        # Should handle gracefully, no circular detection error
        assert "[Circular quote reference detected]" not in result

    def test_circular_reference_missing_uri(self):
        """Test that missing URIs don't cause issues"""
        seen_uris = set()

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                # No URI field
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Post with no URI"},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = ContentProcessor._handle_embed(
            "Original text",
            embed,
            include_image_placeholders=True,
            quote_depth=1,
            seen_uris=seen_uris,
        )

        # Should handle gracefully
        assert isinstance(result, str)


class TestQuoteTextTruncation:
    """Test suite for quote text truncation at different depths"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = ContentProcessor()

    def test_quote_text_truncation_depth_0(self):
        """Test that long quoted text is truncated at depth 0"""
        # At depth 0: max_quote_length = 200 // (0 + 1) = 200
        long_text = "A" * 250  # Longer than 200 chars

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/quoted",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": long_text},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Original post", embed=embed
        )

        # Should truncate to 200 chars + "..."
        assert "Quoting @user.bsky.social" in result
        # The quoted text should be truncated - verify by checking it doesn't contain all 250 As
        assert "A" * 250 not in result
        # Should end with ... (truncation marker)
        assert "..." in result
        # The truncated quote should be approximately 200 chars (plus "...")
        quoted_section = result.split("Quoting @user.bsky.social:")[1].strip()
        # The quoted text line should start with > and be around 200 chars
        assert quoted_section.startswith(">")
        assert len(quoted_section) < 250  # Less than the original

    def test_quote_text_truncation_depth_1(self):
        """Test that long quoted text is truncated more at depth 1"""
        # At depth 1: max_quote_length = 200 // (1 + 1) = 100
        long_text = "B" * 150  # Longer than 100 chars

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": "First level quote",
                    "embed": {
                        "$type": "app.bsky.embed.record",
                        "record": {
                            "uri": "at://did:plc:test/app.bsky.feed.post/postc",
                            "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                            "value": {"text": long_text},
                            "author": {"handle": "userc.bsky.social"},
                        },
                    },
                },
                "author": {"handle": "userb.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Original post", embed=embed
        )

        # Should contain quotes at both levels
        assert "Quoting @userb.bsky.social" in result
        assert "Quoting @userc.bsky.social" in result

        # The deeply nested quote should be truncated more aggressively
        assert "..." in result

    def test_quote_text_no_truncation_short_text(self):
        """Test that short quoted text is not truncated"""
        short_text = "Short quote"

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/quoted",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": short_text},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Original post", embed=embed
        )

        # Should contain the full short text
        assert "Quoting @user.bsky.social" in result
        assert short_text in result


class TestComplexEmbedCombinations:
    """Test suite for complex combinations of embeds (quotes + images + links)"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = ContentProcessor()

    def test_quote_with_images(self):
        """Test quote post that contains images"""
        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/quoted",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": "Check out this image!",
                    "embed": {
                        "$type": "app.bsky.embed.images",
                        "images": [
                            {
                                "alt": "A beautiful landscape",
                                "image": {
                                    "ref": {"$link": "blob123"},
                                    "mimeType": "image/jpeg",
                                },
                            }
                        ],
                    },
                },
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Original post", embed=embed, include_image_placeholders=True
        )

        # Should contain both quote and image placeholder
        assert "Quoting @user.bsky.social" in result
        assert "Check out this image!" in result
        assert "📷 [1 image]" in result
        assert "A beautiful landscape" in result

    def test_quote_with_external_link(self):
        """Test quote post that contains external link"""
        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/quoted",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": "Check out this article",
                    "embed": {
                        "$type": "app.bsky.embed.external",
                        "external": {
                            "uri": "https://example.com/article",
                            "title": "Interesting Article",
                        },
                    },
                },
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Original post", embed=embed
        )

        # Should contain both quote and external link
        assert "Quoting @user.bsky.social" in result
        assert "Check out this article" in result
        assert "https://example.com/article" in result

    def test_record_with_media_images_and_quote(self):
        """Test recordWithMedia embed (quote + images)"""
        embed = {
            "$type": "app.bsky.embed.recordWithMedia",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/quoted",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": "Original quoted post"},
                "author": {"handle": "user.bsky.social"},
            },
            "media": {
                "$type": "app.bsky.embed.images",
                "images": [
                    {
                        "alt": "Image 1",
                        "image": {
                            "ref": {"$link": "blob1"},
                            "mimeType": "image/jpeg",
                        },
                    },
                    {
                        "alt": "Image 2",
                        "image": {
                            "ref": {"$link": "blob2"},
                            "mimeType": "image/png",
                        },
                    },
                ],
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "My post with quote and images",
            embed=embed,
            include_image_placeholders=True,
        )

        # Should contain both quote and images
        assert "Quoting @user.bsky.social" in result
        assert "Original quoted post" in result
        assert "📷 [2 images]" in result
        assert "Image 1" in result
        assert "Image 2" in result

    def test_complex_nested_quote_with_images_and_link(self):
        """Test deeply nested quote with images and external link"""
        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": "Post B with nested content",
                    "embed": {
                        "$type": "app.bsky.embed.recordWithMedia",
                        "record": {
                            "uri": "at://did:plc:test/app.bsky.feed.post/postc",
                            "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                            "value": {"text": "Post C content"},
                            "author": {"handle": "userc.bsky.social"},
                        },
                        "media": {
                            "$type": "app.bsky.embed.images",
                            "images": [
                                {
                                    "alt": "Nested image",
                                    "image": {
                                        "ref": {"$link": "blob123"},
                                        "mimeType": "image/jpeg",
                                    },
                                }
                            ],
                        },
                    },
                },
                "author": {"handle": "userb.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            "Post A", embed=embed, include_image_placeholders=True
        )

        # Should handle all components
        assert "Post A" in result
        assert "Quoting @userb.bsky.social" in result
        assert "Post B with nested content" in result
        # Nested quote and images should also be present
        assert "userc.bsky.social" in result
        assert "📷 [1 image]" in result


class TestCharacterLimitCompliance:
    """Test suite for character limit compliance with nested quotes"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = ContentProcessor()

    def test_nested_quotes_respect_character_limit(self):
        """Test that nested quotes are truncated to respect Mastodon's limit"""
        # Create content that would exceed 500 chars without truncation
        long_text = "A" * 200

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": long_text,
                    "embed": {
                        "$type": "app.bsky.embed.record",
                        "record": {
                            "uri": "at://did:plc:test/app.bsky.feed.post/postc",
                            "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                            "value": {"text": long_text},
                            "author": {"handle": "userc.bsky.social"},
                        },
                    },
                },
                "author": {"handle": "userb.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            long_text,  # Original post also has long text
            embed=embed,
        )

        # Should never exceed Mastodon's character limit
        assert len(result) <= ContentProcessor.MASTODON_CHAR_LIMIT

    def test_character_limit_with_quote_and_attribution(self):
        """Test character limit with quote and sync attribution"""
        long_text = "B" * 250

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/quoted",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {"text": long_text},
                "author": {"handle": "user.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(
            long_text, embed=embed, include_sync_attribution=True
        )

        # Should never exceed limit even with attribution
        assert len(result) <= ContentProcessor.MASTODON_CHAR_LIMIT

        # If there was room, should include attribution
        # (may not be present if content was too long)
        # Just verify it doesn't break the limit

    def test_multiple_nested_quotes_character_limit(self):
        """Test that multiple nested quotes respect character limit"""
        # Create a chain with moderately sized text at each level
        medium_text = "X" * 150

        embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/postb",
                "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                "value": {
                    "text": medium_text,
                    "embed": {
                        "$type": "app.bsky.embed.record",
                        "record": {
                            "uri": "at://did:plc:test/app.bsky.feed.post/postc",
                            "py_type": "app.bsky.feed.defs#postView.ViewRecord",
                            "value": {"text": medium_text},
                            "author": {"handle": "userc.bsky.social"},
                        },
                    },
                },
                "author": {"handle": "userb.bsky.social"},
            },
        }

        result = self.processor.process_bluesky_to_mastodon(medium_text, embed=embed)

        # Must respect character limit
        assert len(result) <= ContentProcessor.MASTODON_CHAR_LIMIT
