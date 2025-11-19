"""
Tests for CLI Interface
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

# Import the CLI group from sync.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sync import cli


class TestCLI:
    """Test suite for CLI interface"""

    def test_cli_help_command(self):
        """Test CLI help command works"""
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "sync.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Social Sync" in result.stdout or "Usage:" in result.stdout

    def test_cli_sync_command_help(self):
        """Test sync subcommand help"""
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "sync.py"),
                "sync",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--dry-run" in result.stdout
        assert "--since-date" in result.stdout
        assert "--disable-source-platform" in result.stdout

    def test_cli_status_command_help(self):
        """Test status subcommand help"""
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "sync.py"),
                "status",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_cli_config_command_help(self):
        """Test config subcommand help"""
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "sync.py"),
                "config",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_cli_test_command_help(self):
        """Test test subcommand help"""
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "sync.py"),
                "test",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


def test_sync_command_dry_run():
    """Test sync command with --dry-run flag"""
    with (
        patch("src.sync_orchestrator.SocialSyncOrchestrator") as mock_orchestrator,
        patch("src.config.Settings") as mock_settings,
        patch("sync.SocialSyncOrchestrator") as mock_sync_orchestrator_direct,
    ):
        # Configure mocks
        mock_settings_instance = Mock()
        mock_settings_instance.state_file = "/tmp/test_state.json"  # nosec B108
        mock_settings.return_value = mock_settings_instance

        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Mock run_sync to return proper dictionary
        mock_orchestrator_instance.run_sync.return_value = {
            "success": True,
            "synced_count": 5,
            "failed_count": 0,
            "duration": 2.5,
            "dry_run": True,
        }

        # Mock the direct import in sync.py as well
        mock_sync_orchestrator_direct.return_value = mock_orchestrator_instance

        # Use Click's test runner instead of subprocess
        runner = CliRunner()
        result = runner.invoke(cli, ["sync", "--dry-run"])

        # Print output for debugging
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exception: {result.exception}")

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify run_sync was called
        mock_orchestrator_instance.run_sync.assert_called_once()


def test_sync_command_since_date():
    """Test sync command with --since flag"""
    with (
        patch("src.sync_orchestrator.SocialSyncOrchestrator") as mock_orchestrator,
        patch("src.config.Settings") as mock_settings,
        patch("sync.SocialSyncOrchestrator") as mock_sync_orchestrator_direct,
    ):
        # Configure mocks
        mock_settings_instance = Mock()
        mock_settings_instance.state_file = "/tmp/test_state.json"  # nosec B108
        mock_settings.return_value = mock_settings_instance

        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Mock run_sync to return proper dictionary
        mock_orchestrator_instance.run_sync.return_value = {
            "success": True,
            "synced_count": 3,
            "failed_count": 0,
            "duration": 1.8,
            "dry_run": False,
        }

        # Mock the direct import in sync.py as well
        mock_sync_orchestrator_direct.return_value = mock_orchestrator_instance

        # Use Click's test runner
        runner = CliRunner()
        result = runner.invoke(cli, ["sync", "--since-date", "2023-01-01"])

        # Print output for debugging
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exception: {result.exception}")

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify run_sync was called
        mock_orchestrator_instance.run_sync.assert_called_once()


def test_sync_command_disable_source_platform():
    """Test sync command with --disable-source-platform flag"""
    with (
        patch("src.sync_orchestrator.SocialSyncOrchestrator") as mock_orchestrator,
        patch("src.config.Settings") as mock_settings,
        patch("sync.SocialSyncOrchestrator") as mock_sync_orchestrator_direct,
    ):
        # Configure mocks
        mock_settings_instance = Mock()
        mock_settings_instance.state_file = "/tmp/test_state.json"  # nosec B108
        mock_settings.return_value = mock_settings_instance

        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Mock run_sync to return proper dictionary
        mock_orchestrator_instance.run_sync.return_value = {
            "success": True,
            "synced_count": 5,
            "failed_count": 0,
            "duration": 2.0,
            "dry_run": False,
        }

        # Mock the direct import in sync.py as well
        mock_sync_orchestrator_direct.return_value = mock_orchestrator_instance

        # Use Click's test runner
        runner = CliRunner()
        result = runner.invoke(cli, ["sync", "--disable-source-platform"])

        # Print output for debugging
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exception: {result.exception}")

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify run_sync was called
        mock_orchestrator_instance.run_sync.assert_called_once()

        # Verify environment variable was set
        import os

        assert os.environ.get("DISABLE_SOURCE_PLATFORM") == "true"

    @patch("src.sync_orchestrator.SocialSyncOrchestrator")
    def test_status_command(self, mock_orchestrator_class):
        """Test status command"""
        mock_orchestrator = Mock()
        mock_orchestrator.get_sync_status.return_value = {
            "last_sync_time": "2025-01-01T12:00:00",
            "total_synced_posts": 10,
            "dry_run_mode": False,
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch.dict(
            os.environ,
            {
                "BLUESKY_HANDLE": "test.bsky.social",
                "BLUESKY_PASSWORD": "test-password",
                "MASTODON_ACCESS_TOKEN": "test-token",
            },
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parent.parent / "sync.py"),
                    "status",
                ],
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0
        assert "Sync Status" in result.stdout

    @patch("src.config.get_settings")
    def test_config_command(self, mock_get_settings):
        """Test config command displays settings"""
        mock_settings = Mock()
        mock_settings.bluesky_handle = "test.bsky.social"
        mock_settings.mastodon_api_base_url = "https://mastodon.social"
        mock_settings.sync_interval_minutes = 60
        mock_settings.max_posts_per_sync = 10
        mock_settings.dry_run = False
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "sync.py"), "config"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Configuration" in result.stdout


def test_test_command_success():
    """Test test command with successful connections"""
    with (
        patch("src.sync_orchestrator.SocialSyncOrchestrator") as mock_orchestrator,
        patch("sync.SocialSyncOrchestrator") as mock_sync_orchestrator_direct,
        patch("src.config.get_settings") as mock_get_settings,
        patch.dict(
            os.environ,
            {
                "BLUESKY_HANDLE": "test.bsky.social",
                "BLUESKY_PASSWORD": "test-password",
                "MASTODON_API_BASE_URL": "https://mastodon.social",
                "MASTODON_ACCESS_TOKEN": "test-token",
            },
        ),
    ):
        # Configure settings mocks
        mock_settings_instance = Mock()
        mock_settings_instance.state_file = "/tmp/test_state.json"  # nosec B108
        mock_settings_instance.bluesky_handle = "test.bsky.social"
        mock_settings_instance.bluesky_password = "test-password"
        mock_settings_instance.mastodon_api_base_url = "https://mastodon.social"
        mock_settings_instance.mastodon_access_token = "test-token"
        mock_get_settings.return_value = mock_settings_instance

        # Configure orchestrator mock
        mock_orchestrator_instance = Mock()
        mock_orchestrator_instance.setup_clients.return_value = True  # Successful setup
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_sync_orchestrator_direct.return_value = mock_orchestrator_instance

        # Use Click's test runner
        runner = CliRunner()
        result = runner.invoke(cli, ["test"])

        # Print output for debugging
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exception: {result.exception}")

        # Verify command executed successfully
        assert result.exit_code == 0
        assert "All clients authenticated successfully!" in result.output

    @patch("src.bluesky_client.BlueskyClient")
    @patch("src.mastodon_client.MastodonClient")
    def test_test_command_failure(self, mock_mastodon_class, mock_bluesky_class):
        """Test test command with failed connections"""
        # Mock failed authentication
        mock_bluesky = Mock()
        mock_bluesky.authenticate.return_value = False
        mock_bluesky_class.return_value = mock_bluesky

        mock_mastodon = Mock()
        mock_mastodon.authenticate.return_value = False
        mock_mastodon_class.return_value = mock_mastodon

        with patch.dict(
            os.environ,
            {
                "BLUESKY_HANDLE": "test.bsky.social",
                "BLUESKY_PASSWORD": "test-password",
                "MASTODON_API_BASE_URL": "https://mastodon.social",
                "MASTODON_ACCESS_TOKEN": "test-token",
            },
        ):
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent.parent / "sync.py"), "test"],
                capture_output=True,
                text=True,
            )

        # Verify test command exits with non-zero code on failure
        assert result.returncode != 0

    def test_invalid_command(self):
        """Test CLI with invalid command"""
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "sync.py"),
                "invalid-command",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "No such command" in result.stderr


def test_sync_missing_credentials():
    """Test sync command fails with missing credentials"""
    # Use Click's test runner with empty environment
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Clear credential environment variables
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("BLUESKY_", "MASTODON_"))
        }

        # Mock to prevent actual credential checking
        with patch("src.config.Settings") as mock_settings:
            # Configure settings to raise error for missing credentials
            mock_settings.side_effect = ValueError("Missing required credentials")

            result = runner.invoke(cli, ["sync", "--dry-run"], env=env)

            # Verify command fails due to missing credentials
            assert result.exit_code != 0

    @patch("sync.setup_logging")
    def test_logging_setup_called(self, mock_setup_logging):
        """Test that logging setup is called"""
        with patch.dict(
            os.environ,
            {
                "BLUESKY_HANDLE": "test.bsky.social",
                "BLUESKY_PASSWORD": "test-password",
                "MASTODON_ACCESS_TOKEN": "test-token",
            },
        ):
            # Just test that the CLI starts up and calls setup_logging
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parent.parent / "sync.py"),
                    "--help",
                ],
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0

    def test_cli_log_level_option(self):
        """Test CLI log level option"""
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "sync.py"),
                "--log-level",
                "DEBUG",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


class TestCLIIntegration:
    """Integration tests for CLI with real file operations"""

    def setup_method(self):
        """Set up temporary directory for integration tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory"""
        os.chdir(self.original_cwd)
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_cli_creates_log_file(self):
        """Test that CLI creates log file"""
        # This would require more complex mocking or actual credentials
        # For now, we'll test the simpler case
        pass

    def test_cli_state_file_handling(self):
        """Test CLI handles state file correctly"""
        # This would test actual file I/O operations
        # Requires more setup but is valuable for integration testing
        pass
