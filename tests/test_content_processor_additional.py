"""
Additional tests for ContentProcessor module to improve coverage
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.content_processor import ContentProcessor


class TestContentProcessorEdgeCases:
    """Additional tests for ContentProcessor edge cases to improve coverage"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = ContentProcessor()

    def test_text_exactly_at_character_limit(self):
        """Test text processing when exactly at Mastodon character limit"""
        # Text exactly at the limit
        text_at_limit = "A" * ContentProcessor.MASTODON_CHAR_LIMIT
        processed = self.processor.process_bluesky_to_mastodon(text_at_limit)

        assert len(processed) == ContentProcessor.MASTODON_CHAR_LIMIT
        assert processed == text_at_limit

    def test_text_just_over_character_limit(self):
        """Test text processing when just over the character limit"""
        # Text just over the limit
        text_over_limit = "A" * (ContentProcessor.MASTODON_CHAR_LIMIT + 1)
        processed = self.processor.process_bluesky_to_mastodon(text_over_limit)

        assert len(processed) <= ContentProcessor.MASTODON_CHAR_LIMIT
        # Verify text is truncated with ellipsis when over limit
        assert processed.endswith("...")

    def test_text_with_sync_attribution_at_limit(self):
        """Test text that becomes over limit after sync attribution is added"""
        # Create text that leaves room for attribution
        # Attribution "\n\n(via Bluesky 🦋)" is ~17 chars
        base_text = "A" * (ContentProcessor.MASTODON_CHAR_LIMIT - 25)  # Leave more room
        processed = self.processor.process_bluesky_to_mastodon(
            base_text, include_sync_attribution=True
        )

        # Should include attribution since there's room
        assert len(processed) <= ContentProcessor.MASTODON_CHAR_LIMIT
        assert "(via Bluesky 🦋)" in processed

    def test_malformed_embed_data_handling(self):
        """Test processing of malformed embed data"""
        malformed_embeds = [
            {"malformed": "data"},  # Missing expected structure
            {"$type": "unknown_type"},  # Unknown embed type
            {"external": {"uri": ""}},  # Empty URI
            {"external": {"title": "No URI"}},  # Missing URI
            {},  # Empty embed
            {"external": None},  # Null external data
            {"external": {"uri": None}},  # Null URI
        ]

        base_text = "Test text"

        for embed in malformed_embeds:
            # Should handle gracefully without throwing exceptions
            processed = self.processor.process_bluesky_to_mastodon(
                base_text, embed=embed
            )
            assert isinstance(processed, str)
            assert base_text in processed

    def test_invalid_url_patterns_extraction(self):
        """Test URL extraction with various invalid URL patterns"""
        invalid_url_cases = [
            ("Check out ftp://example.com", []),  # Non-HTTP protocol
            ("Visit www.example.com", []),  # No protocol
            ("See http://", []),  # Incomplete URL
            (
                "Link: http://[invalid",
                ["http://[invalid"],
            ),  # Malformed but starts with http
            ("text://not-a-url", []),  # Not a URL
            ("https://", []),  # Incomplete HTTPS
            ("http:// space.com", []),  # Space in URL (invalid)
        ]

        for text, expected_urls in invalid_url_cases:
            extracted_urls = self.processor.extract_urls(text)
            assert extracted_urls == expected_urls

    def test_mention_extraction_edge_cases(self):
        """Test mention extraction with various edge cases"""
        mention_test_cases = [
            ("@", []),  # Just @ symbol
            ("@ user", []),  # @ with space
            (
                "@user@domain",
                ["user", "domain"],
            ),  # Multiple @ symbols - pattern matches both parts
            ("email@example.com", ["example.com"]),  # Email (picked up by pattern)
            (
                "@verylongusernamethatmightbreak.bsky.social",
                ["verylongusernamethatmightbreak.bsky.social"],
            ),
            (
                "@@doubleatsign",
                ["doubleatsign"],
            ),  # Double @ at start - pattern matches the second part
            ("text@middle.com", ["middle.com"]),  # @ in middle
            (
                "@user.bsky.socialextratext",
                ["user.bsky.socialextratext"],
            ),  # Handle with extra text
            ("@123numeric.com", ["123numeric.com"]),  # Numeric start
            ("@-invalid.com", []),  # Invalid character start
        ]

        for text, expected_mentions in mention_test_cases:
            extracted_mentions = self.processor.extract_mentions(text)
            assert extracted_mentions == expected_mentions

    def test_hashtag_extraction_edge_cases(self):
        """Test hashtag extraction with various edge cases"""
        hashtag_test_cases = [
            ("#", []),  # Just # symbol
            ("# space", []),  # # with space
            (
                "#hashtag#another",
                ["hashtag", "another"],
            ),  # Adjacent hashtags - pattern matches both
            ("#123", ["123"]),  # Numeric hashtag
            ("#_underscore", ["_underscore"]),  # Underscore hashtag
            (
                "#-invalid",
                ["-invalid"],
            ),  # Dash character - pattern matches non-space/hash chars
            ("##double", []),  # Double # at start
            ("text#middle", []),  # # in middle (no space before)
            ("#emoji🦋test", ["emoji🦋test"]),  # Emoji in hashtag
            (
                "#verylonghashtagnamethatmightbreakthingsorsomething",
                ["verylonghashtagnamethatmightbreakthingsorsomething"],
            ),
        ]

        for text, expected_hashtags in hashtag_test_cases:
            extracted_hashtags = self.processor.extract_hashtags(text)
            assert extracted_hashtags == expected_hashtags

    def test_complex_facets_data_handling(self):
        """Test processing of complex facets data"""
        complex_facets_cases = [
            [],  # Empty facets
            [{"no_index": "invalid"}],  # Missing index
            [{"index": {"byteStart": 0}}],  # Missing byteEnd
            [{"index": {"byteStart": 10, "byteEnd": 5}}],  # Invalid range (start > end)
            [
                {"index": {"byteStart": 0, "byteEnd": 100}, "features": []}
            ],  # Empty features
            [
                {
                    "index": {"byteStart": 0, "byteEnd": 5},
                    "features": [{"$type": "unknown"}],
                }
            ],  # Unknown feature type
            [{"index": {"byteStart": None, "byteEnd": None}}],  # Null indices
        ]

        base_text = "Test text with some content"

        for facets in complex_facets_cases:
            # Should handle gracefully without throwing exceptions
            processed = self.processor.process_bluesky_to_mastodon(
                base_text, facets=facets
            )
            assert isinstance(processed, str)

    def test_image_extraction_edge_cases(self):
        """Test image extraction from various embed structures"""
        image_embed_cases = [
            {},  # Empty embed
            {"images": []},  # Empty images array
            {"images": [{}]},  # Empty image object
            {"images": [{"image": {}}]},  # Empty image data
            {"images": [{"image": {"ref": None}}]},  # Null ref
            {"images": [{"image": {"ref": {"$link": None}}}]},  # Null link
            {"images": [{"alt": "Alt text only"}]},  # Missing image data
            {
                "images": [
                    {"image": {"ref": {"$link": "valid_ref"}}, "alt": "Alt text"}
                ]
            },  # Valid case
            {"images": None},  # Null images
        ]

        for embed in image_embed_cases:
            # Should handle gracefully without throwing exceptions
            images = self.processor.extract_images_from_embed(embed)
            assert isinstance(images, list)

    def test_sync_attribution_edge_cases(self):
        """Test sync attribution with various edge cases"""
        attribution_test_cases = [
            ("", "Bluesky"),  # Empty text
            ("Short", "Twitter"),  # Different source
            ("A" * 400, "Bluesky"),  # Long text
            ("Text with\nnewlines\n", "Mastodon"),  # Text with newlines
            ("Text with emoji 🦋", "Bluesky"),  # Text with emoji
        ]

        for text, source in attribution_test_cases:
            attributed = self.processor.add_sync_attribution(text, source)
            assert f"(via {source}" in attributed
            assert text in attributed or len(text) == 0

    def test_external_link_embed_handling(self):
        """Test handling of external link embeds"""
        external_link_cases = [
            {
                "external": {
                    "uri": "https://example.com",
                    "title": "Example Site",
                    "description": "A test site",
                }
            },
            {
                "external": {
                    "uri": "https://example.com",
                    "title": "",  # Empty title
                    "description": "Description only",
                }
            },
            {
                "external": {
                    "uri": "https://example.com",
                    # Missing title and description
                }
            },
            {"external": {"uri": "", "title": "Title without URI"}},  # Empty URI
        ]

        base_text = "Check this out: "

        for embed in external_link_cases:
            processed = self.processor.process_bluesky_to_mastodon(
                base_text, embed=embed
            )
            assert isinstance(processed, str)
            assert base_text in processed

    @patch("src.content_processor.requests.get")
    def test_download_image_error_handling(self, mock_get):
        """Test image download error handling"""
        # Test network error
        mock_get.side_effect = Exception("Network error")

        result = ContentProcessor.download_image("https://example.com/image.jpg")
        assert result is None

        # Test timeout error
        mock_get.side_effect = TimeoutError("Request timeout")

        result = ContentProcessor.download_image("https://example.com/image.jpg")
        assert result is None

        # Test HTTP error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response

        result = ContentProcessor.download_image("https://example.com/image.jpg")
        assert result is None

    def test_mention_conversion_edge_cases(self):
        """Test mention conversion with various patterns"""
        mention_conversion_cases = [
            ("@user.bsky.social", "@user.bsky.social"),  # Standard mention
            ("@user@domain.com", "@user@domain.com"),  # Email-like format
            ("Check out @test.handle", "Check out @test.handle"),  # In sentence
            (
                "Multiple @user1.bsky.social and @user2.handle mentions",
                "Multiple @user1.bsky.social and @user2.handle mentions",
            ),
            ("", ""),  # Empty string
            ("No mentions here", "No mentions here"),  # No mentions
        ]

        for input_text, expected_output in mention_conversion_cases:
            # The _convert_mentions method is private, so we test through the main method
            processed = self.processor.process_bluesky_to_mastodon(input_text)
            # Basic check that it doesn't crash and returns a string
            assert isinstance(processed, str)

    def test_facets_url_expansion_edge_cases(self):
        """Test URL expansion from facets with edge cases"""
        facets_test_cases = [
            # Valid facet with link
            {
                "text": "Check out example.com/short",
                "facets": [
                    {
                        "index": {"byteStart": 10, "byteEnd": 27},
                        "features": [
                            {
                                "$type": "app.bsky.richtext.facet#link",
                                "uri": "https://example.com/very/long/url/path",
                            }
                        ],
                    }
                ],
            },
            # Facet with invalid byte range
            {
                "text": "Short text",
                "facets": [
                    {
                        "index": {
                            "byteStart": 100,
                            "byteEnd": 200,
                        },  # Beyond text length
                        "features": [
                            {
                                "$type": "app.bsky.richtext.facet#link",
                                "uri": "https://example.com",
                            }
                        ],
                    }
                ],
            },
            # Facet with missing URI
            {
                "text": "Text with link",
                "facets": [
                    {
                        "index": {"byteStart": 0, "byteEnd": 4},
                        "features": [
                            {
                                "$type": "app.bsky.richtext.facet#link"
                                # Missing uri field
                            }
                        ],
                    }
                ],
            },
        ]

        for test_case in facets_test_cases:
            processed = self.processor.process_bluesky_to_mastodon(
                test_case["text"], facets=test_case["facets"]
            )
            assert isinstance(processed, str)

    def test_image_embed_with_alt_text(self):
        """Test image embed processing with alt text"""
        image_embed = {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "alt": "A beautiful sunset",
                    "image": {
                        "ref": {"$link": "blob_reference_123"},
                        "mimeType": "image/jpeg",
                        "size": 123456,
                    },
                }
            ],
        }

        processed = self.processor.process_bluesky_to_mastodon(
            "Beautiful photo:", embed=image_embed, include_image_placeholders=True
        )

        assert isinstance(processed, str)
        # Verify image placeholder is included in processed content
        assert "📷" in processed

    def test_record_embed_handling(self):
        """Test handling of record embeds (quoted posts)"""
        record_embed = {
            "$type": "app.bsky.embed.record",
            "record": {
                "uri": "at://did:plc:test/app.bsky.feed.post/123",
                "cid": "test_cid",
            },
        }

        processed = self.processor.process_bluesky_to_mastodon(
            "Quoting this post:", embed=record_embed
        )

        assert isinstance(processed, str)
        # Verify record embeds are handled gracefully without errors
        assert len(processed) > 0
