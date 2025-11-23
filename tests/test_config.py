"""
Tests for Configuration Management
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import Settings


class TestSettings:
    """Test the Settings configuration class"""

    def setup_method(self):
        """Clean up environment before each test"""
        # Store original environment
        self.original_env = os.environ.copy()

        # Clear all social sync related env vars
        for key in list(os.environ.keys()):
            if key.upper().startswith(
                ("BLUESKY_", "MASTODON_", "SYNC_", "MAX_POSTS", "DRY_RUN", "LOG_LEVEL")
            ):
                del os.environ[key]

    def teardown_method(self):
        """Restore environment after each test"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_settings_with_valid_config(self):
        """Test Settings initialization with valid configuration"""
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        settings = Settings()

        assert settings.bluesky_handle == "test.bsky.social"
        assert settings.bluesky_password == "test-password"
        assert settings.mastodon_access_token == "test-token"

    def test_settings_defaults(self):
        """Test Settings with code defaults (no environment variables)"""
        # Set only required fields and ensure others are not set
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Explicitly clear environment variables that might override defaults
        env_vars_to_clear = [
            "DRY_RUN",
            "SYNC_INTERVAL_MINUTES",
            "MAX_POSTS_PER_SYNC",
            "LOG_LEVEL",
            "STATE_FILE",
            "MASTODON_API_BASE_URL",
            "SYNC_START_DATE",
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

        # Create settings with _env_file=None to prevent .env file loading
        settings = Settings(_env_file=None)

        # Test code defaults (not .env file values)
        assert settings.sync_interval_minutes == 60
        assert settings.max_posts_per_sync == 10
        assert settings.dry_run is False  # Code default
        assert settings.log_level == "INFO"
        assert settings.state_file == "sync_state.json"
        assert (
            settings.mastodon_api_base_url == "https://mastodon.social"
        )  # Code default
        assert settings.sync_start_date is None  # Code default

    def test_settings_custom_values(self):
        """Test Settings with custom environment values"""
        os.environ["BLUESKY_HANDLE"] = "custom.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "custom-password"
        os.environ["MASTODON_API_BASE_URL"] = "https://custom.social"
        os.environ["MASTODON_ACCESS_TOKEN"] = "custom-token"
        os.environ["SYNC_INTERVAL_MINUTES"] = "30"
        os.environ["MAX_POSTS_PER_SYNC"] = "50"
        os.environ["DRY_RUN"] = "true"
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["STATE_FILE"] = "custom_state.json"

        settings = Settings()

        assert settings.bluesky_handle == "custom.bsky.social"
        assert settings.bluesky_password == "custom-password"
        assert settings.mastodon_api_base_url == "https://custom.social"
        assert settings.mastodon_access_token == "custom-token"
        assert settings.sync_interval_minutes == 30
        assert settings.max_posts_per_sync == 50
        assert settings.dry_run is True
        assert settings.log_level == "DEBUG"
        assert settings.state_file == "custom_state.json"

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive"""
        os.environ["bluesky_handle"] = "test.bsky.social"  # lowercase
        os.environ["BLUESKY_PASSWORD"] = "test-password"  # uppercase
        os.environ["Mastodon_Access_Token"] = "test-token"  # mixed case

        settings = Settings()

        assert settings.bluesky_handle == "test.bsky.social"
        assert settings.bluesky_password == "test-password"
        assert settings.mastodon_access_token == "test-token"

    def test_boolean_env_var_parsing(self):
        """Test that boolean environment variables are parsed correctly"""
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Test various boolean string representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_value, expected in test_cases:
            os.environ["DRY_RUN"] = env_value
            settings = Settings()
            assert (
                settings.dry_run == expected
            ), f"Failed for {env_value}: expected {expected}, got {settings.dry_run}"

    def test_integer_env_var_parsing(self):
        """Test that integer environment variables are parsed correctly"""
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        test_cases = [
            ("15", 15),
            ("30", 30),
            ("60", 60),
        ]

        for env_value, expected in test_cases:
            os.environ["SYNC_INTERVAL_MINUTES"] = env_value
            settings = Settings()
            assert settings.sync_interval_minutes == expected

    def test_sync_start_date_format_validation(self):
        """Test that SYNC_START_DATE formats from .env.example are properly validated"""
        # Set required credentials for Settings initialization
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Test valid date formats from .env.example
        valid_formats = [
            # Date only format: SYNC_START_DATE=2025-01-01
            ("2025-01-01", datetime(2025, 1, 1, 0, 0, 0)),
            ("2025-12-31", datetime(2025, 12, 31, 0, 0, 0)),
            # Datetime format without timezone: SYNC_START_DATE=2025-01-15T10:30:00
            ("2025-01-15T10:30:00", datetime(2025, 1, 15, 10, 30, 0)),
            ("2025-06-20T23:59:59", datetime(2025, 6, 20, 23, 59, 59)),
            # Datetime with timezone: SYNC_START_DATE=2025-01-15T10:30:00-05:00
            (
                "2025-01-15T10:30:00-05:00",
                datetime(2025, 1, 15, 15, 30, 0),
            ),  # UTC conversion
            (
                "2025-01-15T10:30:00+02:00",
                datetime(2025, 1, 15, 8, 30, 0),
            ),  # UTC conversion
            (
                "2025-01-15T10:30:00Z",
                datetime(2025, 1, 15, 10, 30, 0),
            ),  # Z format (UTC)
        ]

        for date_str, expected_datetime in valid_formats:
            os.environ["SYNC_START_DATE"] = date_str
            settings = Settings(_env_file=None)  # Prevent .env file loading

            # Test that validation passes
            assert (
                settings.sync_start_date == date_str
            ), f"Failed to store date string: {date_str}"

            # Test that datetime conversion works correctly
            result_datetime = settings.get_sync_start_datetime()
            assert isinstance(
                result_datetime, datetime
            ), f"Expected datetime object for: {date_str}"

            # Convert to UTC naive datetime for comparison
            if result_datetime.tzinfo is not None:
                result_datetime = result_datetime.astimezone(timezone.utc).replace(
                    tzinfo=None
                )

            assert result_datetime == expected_datetime, (
                f"Date conversion failed for {date_str}: "
                f"expected {expected_datetime}, got {result_datetime}"
            )

    def test_sync_start_date_invalid_formats(self):
        """Test that invalid SYNC_START_DATE formats are properly rejected"""
        # Set required credentials for Settings initialization
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Test invalid date formats
        invalid_formats = [
            "2025-13-01",  # Invalid month
            "2025-01-32",  # Invalid day
            "2025/01/01",  # Wrong separator
            "01-01-2025",  # Wrong order
            "2025-1-1",  # Missing zero padding
            "2025-01-01 10:30",  # Space separator instead of T
            "not-a-date",  # Non-date string
            "2025-01-01T25:00:00",  # Invalid hour
            "2025-01-01T10:60:00",  # Invalid minute
            "2025-01-01T10:30:60",  # Invalid second
            "",  # Empty string
            "2025",  # Year only
            "01-01",  # Month-day only
        ]

        for invalid_date in invalid_formats:
            os.environ["SYNC_START_DATE"] = invalid_date

            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)  # Prevent .env file loading

            # Verify the error message mentions the expected format
            error_message = str(exc_info.value)
            assert "sync_start_date must be in ISO format" in error_message, (
                f"Expected ISO format error message for invalid date: {invalid_date}, "
                f"but got: {error_message}"
            )

    def test_sync_start_date_edge_cases(self):
        """Test edge cases for SYNC_START_DATE handling"""
        # Set required credentials for Settings initialization
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Test None/unset case - prevent .env file loading
        if "SYNC_START_DATE" in os.environ:
            del os.environ["SYNC_START_DATE"]
        settings = Settings(_env_file=None)  # Prevent .env file loading
        assert settings.sync_start_date is None

        # get_sync_start_datetime() should return 7 days ago when None
        result = settings.get_sync_start_datetime()
        assert isinstance(result, datetime)
        # Verify it's approximately 7 days ago (within a few minutes tolerance)
        expected_timestamp = time.time() - (7 * 24 * 60 * 60)  # 7 days ago
        actual_timestamp = result.timestamp()
        assert (
            abs(actual_timestamp - expected_timestamp) < 300
        ), f"Expected approximately 7 days ago, got {result}"  # 5 minutes tolerance

        # Test leap year date
        os.environ["SYNC_START_DATE"] = "2024-02-29"  # Valid leap year date
        settings = Settings(_env_file=None)
        result = settings.get_sync_start_datetime()
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29

        # Test beginning/end of year
        test_cases = [
            ("2025-01-01T00:00:00", datetime(2025, 1, 1, 0, 0, 0)),
            ("2025-12-31T23:59:59", datetime(2025, 12, 31, 23, 59, 59)),
        ]

        for date_str, expected in test_cases:
            os.environ["SYNC_START_DATE"] = date_str
            settings = Settings(_env_file=None)
            result = settings.get_sync_start_datetime()
            # Convert to UTC naive datetime for comparison if timezone-aware
            if result.tzinfo is not None:
                result = result.astimezone(timezone.utc).replace(tzinfo=None)
            assert result == expected, f"Edge case failed for {date_str}"

    def test_image_upload_failure_strategy_validation(self):
        """Test validation of image_upload_failure_strategy"""
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Valid strategies should work
        valid_strategies = ["skip_post", "partial", "text_placeholder"]
        for strategy in valid_strategies:
            os.environ["IMAGE_UPLOAD_FAILURE_STRATEGY"] = strategy
            settings = Settings(_env_file=None)
            assert settings.image_upload_failure_strategy == strategy

        # Invalid strategy should raise error
        os.environ["IMAGE_UPLOAD_FAILURE_STRATEGY"] = "invalid_strategy"
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        assert "image_upload_failure_strategy" in str(exc_info.value)

    def test_image_upload_max_retries_default(self):
        """Test default value for image_upload_max_retries"""
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        settings = Settings(_env_file=None)
        assert settings.image_upload_max_retries == 3

    def test_image_upload_max_retries_custom(self):
        """Test custom value for image_upload_max_retries"""
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"
        os.environ["IMAGE_UPLOAD_MAX_RETRIES"] = "5"

        settings = Settings(_env_file=None)
        assert settings.image_upload_max_retries == 5
