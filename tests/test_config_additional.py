"""
Additional tests for Configuration module to improve coverage
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add the parent directory to sys.path to import src as a package
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import ConfigurationError, Settings, check_env_file_exists, get_settings


class TestConfigurationEdgeCases:
    """Additional tests for configuration edge cases to improve coverage"""

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

    def test_empty_environment_variables(self):
        """Test that empty environment variables trigger validation errors"""
        os.environ["BLUESKY_HANDLE"] = ""
        os.environ["BLUESKY_PASSWORD"] = ""
        os.environ["MASTODON_ACCESS_TOKEN"] = ""

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Check that all three required fields are in the error
        error_str = str(exc_info.value)
        assert "bluesky_handle" in error_str
        assert "bluesky_password" in error_str
        assert "mastodon_access_token" in error_str

    def test_placeholder_values_rejected(self):
        """Test that example placeholder values are rejected"""
        os.environ["BLUESKY_HANDLE"] = "your-handle.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "your-app-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "your-access-token"

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_str = str(exc_info.value)
        assert "Please set a valid" in error_str

    def test_invalid_sync_start_date_formats(self):
        """Test various invalid sync start date formats"""
        # Set valid credentials first
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        invalid_dates = [
            "invalid-date",
            "2023-13-01",  # Invalid month
            "2023-01-32",  # Invalid day
            "2023/01/01",  # Wrong format
            "01-01-2023",  # Wrong format
            "2023-1-1",  # Wrong format (should be zero-padded)
            "not-a-date-at-all",
        ]

        for invalid_date in invalid_dates:
            os.environ["SYNC_START_DATE"] = invalid_date
            with pytest.raises((ValidationError, ValueError)):
                Settings()

    def test_valid_edge_case_values(self):
        """Test valid edge case configuration values"""
        os.environ["BLUESKY_HANDLE"] = "a.bsky.social"  # Minimal valid handle
        os.environ["BLUESKY_PASSWORD"] = "x"  # Minimal password
        os.environ["MASTODON_ACCESS_TOKEN"] = "y"  # Minimal token
        os.environ["SYNC_START_DATE"] = "2023-01-01T00:00:00"  # Valid ISO format
        os.environ["MAX_POSTS_PER_SYNC"] = "1"  # Minimal
        os.environ["SYNC_INTERVAL_MINUTES"] = "1"  # Minimal

        settings = Settings()
        assert settings.bluesky_handle == "a.bsky.social"
        assert settings.max_posts_per_sync == 1
        assert settings.sync_interval_minutes == 1

        # Test sync date functionality
        sync_datetime = settings.get_sync_start_datetime()
        assert isinstance(sync_datetime, datetime)
        assert sync_datetime.year == 2023

    def test_get_settings_configuration_error_no_env_file(self):
        """Test get_settings() raises ConfigurationError when no .env file exists"""
        # Clear environment to trigger error
        for key in list(os.environ.keys()):
            if key.upper().startswith(("BLUESKY_", "MASTODON_")):
                del os.environ[key]

        # Test in a directory without .env file
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with pytest.raises(ConfigurationError) as exc_info:
                    get_settings()

                error_msg = str(exc_info.value)
                assert "Configuration file missing" in error_msg
                assert "cp .env.example .env" in error_msg
            finally:
                os.chdir(original_cwd)

    def test_get_settings_configuration_error_with_env_file(self):
        """Test get_settings() raises ConfigurationError when .env exists but credentials missing"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                # Create an .env file but don't set credentials in environment
                with open(".env", "w") as f:
                    f.write("# Empty env file\n")

                with pytest.raises(ConfigurationError) as exc_info:
                    get_settings()

                error_msg = str(exc_info.value)
                assert "Configuration incomplete" in error_msg
                assert "BLUESKY_HANDLE" in error_msg
            finally:
                os.chdir(original_cwd)

    def test_check_env_file_exists_function(self):
        """Test check_env_file_exists() function in different scenarios"""
        original_cwd = os.getcwd()

        # Test when .env doesn't exist
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            assert check_env_file_exists() is False

            # Create a .env file and test again
            with open(".env", "w") as f:
                f.write("TEST=value\n")

            assert check_env_file_exists() is True

        os.chdir(original_cwd)

    def test_sync_start_date_validation_edge_cases(self):
        """Test sync start date validation with various edge cases"""
        # Set required credentials
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Test valid date formats
        valid_dates = [
            "2023-01-01",
            "2023-12-31",
            "2023-01-01T00:00:00",
            "2023-12-31T23:59:59",
        ]

        for valid_date in valid_dates:
            os.environ["SYNC_START_DATE"] = valid_date
            settings = Settings()
            sync_datetime = settings.get_sync_start_datetime()
            assert isinstance(sync_datetime, datetime)

    def test_configuration_with_all_optional_fields(self):
        """Test configuration with all optional fields set"""
        env_vars = {
            "BLUESKY_HANDLE": "test.bsky.social",
            "BLUESKY_PASSWORD": "test-password",
            "MASTODON_API_BASE_URL": "https://custom.mastodon.social",
            "MASTODON_ACCESS_TOKEN": "test-token",
            "SYNC_INTERVAL_MINUTES": "30",
            "MAX_POSTS_PER_SYNC": "50",
            "SYNC_START_DATE": "2023-06-01T12:00:00",
            "DRY_RUN": "true",
            "LOG_LEVEL": "DEBUG",
            "STATE_FILE": "custom_state.json",
        }

        for key, value in env_vars.items():
            os.environ[key] = value

        settings = Settings()

        # Verify all settings are correctly set
        assert settings.bluesky_handle == "test.bsky.social"
        assert settings.bluesky_password == "test-password"
        assert settings.mastodon_api_base_url == "https://custom.mastodon.social"
        assert settings.mastodon_access_token == "test-token"
        assert settings.sync_interval_minutes == 30
        assert settings.max_posts_per_sync == 50
        assert settings.dry_run is True
        assert settings.log_level == "DEBUG"
        assert settings.state_file == "custom_state.json"

        # Test sync date parsing
        sync_datetime = settings.get_sync_start_datetime()
        assert sync_datetime.year == 2023
        assert sync_datetime.month == 6
        assert sync_datetime.day == 1
        assert sync_datetime.hour == 12

    def test_boolean_environment_variable_parsing(self):
        """Test boolean environment variable parsing edge cases"""
        # Set required credentials
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Test various boolean representations
        boolean_test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
        ]

        for bool_str, expected in boolean_test_cases:
            os.environ["DRY_RUN"] = bool_str
            settings = Settings()
            assert settings.dry_run is expected, f"Expected {expected} for '{bool_str}'"

    def test_integer_environment_variable_parsing(self):
        """Test integer environment variable parsing edge cases"""
        # Set required credentials
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        # Test various integer representations
        int_test_cases = [
            ("1", 1),
            ("100", 100),
            ("0", 0),  # Edge case: zero
            ("-1", -1),  # Negative numbers are valid integers
        ]

        for int_str, expected in int_test_cases:
            os.environ["MAX_POSTS_PER_SYNC"] = int_str
            settings = Settings()
            assert settings.max_posts_per_sync == expected

        # Test invalid integer values that should raise ValidationError
        invalid_int_values = ["not_a_number", "1.5", "abc123", ""]

        for invalid_int in invalid_int_values:
            os.environ["MAX_POSTS_PER_SYNC"] = invalid_int
            with pytest.raises(ValidationError):
                Settings()
