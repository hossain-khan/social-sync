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
from sync import ENV_TEMPLATE, _cli_name, cli


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


def test_status_command():
    """Test status command"""
    with (
        patch("sync.SocialSyncOrchestrator") as mock_orchestrator_class,
        patch.dict(
            os.environ,
            {
                "BLUESKY_HANDLE": "test.bsky.social",
                "BLUESKY_PASSWORD": "test-password",
                "MASTODON_ACCESS_TOKEN": "test-token",
            },
        ),
    ):
        mock_orchestrator = Mock()
        mock_orchestrator.get_sync_status.return_value = {
            "last_sync_time": "2025-01-01T12:00:00",
            "total_synced_posts": 10,
            "dry_run_mode": False,
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        # Print output for debugging
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exception: {result.exception}")

        assert result.exit_code == 0
        assert "Sync Status" in result.output


def test_config_command():
    """Test config command displays settings"""
    with (
        patch("sync.get_settings") as mock_get_settings,
        patch.dict(
            os.environ,
            {
                "BLUESKY_HANDLE": "test.bsky.social",
                "BLUESKY_PASSWORD": "test-password",
                "MASTODON_ACCESS_TOKEN": "test-token",
            },
        ),
    ):
        mock_settings = Mock()
        mock_settings.bluesky_handle = "test.bsky.social"
        mock_settings.mastodon_api_base_url = "https://mastodon.social"
        mock_settings.sync_interval_minutes = 60
        mock_settings.max_posts_per_sync = 10
        mock_settings.dry_run = False
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        runner = CliRunner()
        result = runner.invoke(cli, ["config"])

        # Print output for debugging
        if result.exit_code != 0:
            print(f"Command output: {result.output}")
            print(f"Exception: {result.exception}")

        assert result.exit_code == 0
        assert "Configuration" in result.output


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


def test_test_command_failure():
    """Test test command with failed connections"""
    with (
        patch("sync.SocialSyncOrchestrator") as mock_orchestrator,
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
        # Mock failed client setup
        mock_orchestrator_instance = Mock()
        mock_orchestrator_instance.setup_clients.return_value = False
        mock_orchestrator.return_value = mock_orchestrator_instance

        runner = CliRunner()
        result = runner.invoke(cli, ["test"])

        # Verify test command exits with non-zero code on failure
        assert result.exit_code != 0


def test_invalid_command():
    """Test CLI with invalid command"""
    runner = CliRunner()
    result = runner.invoke(cli, ["invalid-command"])

    assert result.exit_code != 0
    assert "No such command" in result.output


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


def test_logging_setup_called():
    """Test that logging setup is called and CLI starts correctly"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0


def test_cli_log_level_option():
    """Test CLI log level option"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--log-level", "DEBUG", "--help"])

    assert result.exit_code == 0


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


class TestEnvTemplate:
    """Tests for the embedded ENV_TEMPLATE constant."""

    def test_env_template_contains_required_keys(self):
        """ENV_TEMPLATE must include all required credential keys."""
        required = [
            "BLUESKY_HANDLE",
            "BLUESKY_PASSWORD",
            "MASTODON_API_BASE_URL",
            "MASTODON_ACCESS_TOKEN",
        ]
        for key in required:
            assert key in ENV_TEMPLATE, f"{key} missing from ENV_TEMPLATE"

    def test_env_template_contains_common_settings(self):
        """ENV_TEMPLATE should include common optional settings."""
        for key in (
            "SYNC_INTERVAL_MINUTES",
            "MAX_POSTS_PER_SYNC",
            "DRY_RUN",
            "LOG_LEVEL",
        ):
            assert key in ENV_TEMPLATE, f"{key} missing from ENV_TEMPLATE"

    def test_env_template_is_non_empty_string(self):
        assert isinstance(ENV_TEMPLATE, str) and len(ENV_TEMPLATE) > 0


class TestCliName:
    """Tests for the _cli_name() helper."""

    def test_cli_name_returns_string(self):
        assert isinstance(_cli_name(), str)

    def test_cli_name_not_frozen(self):
        """When not frozen (normal Python), returns 'python sync.py'."""
        with patch("sys.frozen", False, create=True):
            assert _cli_name() == "python sync.py"

    def test_cli_name_frozen(self):
        """When frozen (PyInstaller binary), returns the executable filename."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "argv", ["/home/user/tools/social-sync", "setup"]):
                assert _cli_name() == "social-sync"


class TestSetupCommand:
    """Tests for the `setup` CLI command in standalone / no-repo mode."""

    def test_setup_creates_env_file(self):
        """setup writes a .env file from the embedded template."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["setup"], input="n\n")
            assert result.exit_code == 0, result.output
            assert Path(".env").exists()

    def test_setup_env_file_contains_required_keys(self):
        """The .env file written by setup must contain required credential keys."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli, ["setup"], input="n\n")
            content = Path(".env").read_text()
            for key in (
                "BLUESKY_HANDLE",
                "BLUESKY_PASSWORD",
                "MASTODON_ACCESS_TOKEN",
                "MASTODON_API_BASE_URL",
            ):
                assert key in content

    def test_setup_does_not_require_env_example(self):
        """setup must succeed even when .env.example is absent (standalone mode)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            assert not Path(".env.example").exists()
            result = runner.invoke(cli, ["setup"], input="n\n")
            assert result.exit_code == 0
            assert "Error" not in result.output

    def test_setup_prompts_before_overwrite(self):
        """setup asks for confirmation when .env already exists."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text("EXISTING=1\n")
            result = runner.invoke(cli, ["setup"], input="n\n")  # decline overwrite
            assert result.exit_code == 0
            assert "already exists" in result.output
            # Original file must be untouched
            assert Path(".env").read_text() == "EXISTING=1\n"

    def test_setup_overwrites_on_confirm(self):
        """setup replaces .env when the user confirms."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text("EXISTING=1\n")
            result = runner.invoke(
                cli, ["setup"], input="y\nn\n"
            )  # confirm overwrite, skip editor
            assert result.exit_code == 0
            content = Path(".env").read_text()
            assert "BLUESKY_HANDLE" in content

    def test_setup_shows_github_url(self):
        """Hint shown after setup must point to the GitHub docs URL."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["setup"], input="n\n")
            assert "github.com/hossain-khan/social-sync" in result.output
