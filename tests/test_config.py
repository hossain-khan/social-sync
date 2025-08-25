"""
Tests for Configuration Management
"""

import os
import sys
from pathlib import Path

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
        """Test Settings with default values"""
        # Set required fields
        os.environ["BLUESKY_HANDLE"] = "test.bsky.social"
        os.environ["BLUESKY_PASSWORD"] = "test-password"
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"

        settings = Settings()

        # Test defaults
        assert settings.sync_interval_minutes == 15
        assert settings.max_posts_per_sync == 10  # Correct default value
        assert settings.dry_run is False  # Correct default value
        assert settings.log_level == "INFO"
        assert settings.state_file == "sync_state.json"

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
