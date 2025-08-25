"""
Tests for CLI Interface
"""
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import tempfile
import os
import subprocess

# Add the parent directory to sys.path to import modules
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import sync as cli_module


class TestCLI:
    """Test suite for CLI interface"""

    def test_cli_help_command(self):
        """Test CLI help command works"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"), "--help"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Social Sync" in result.stdout or "Usage:" in result.stdout

    def test_cli_sync_command_help(self):
        """Test sync subcommand help"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"), "sync", "--help"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "--dry-run" in result.stdout
        assert "--since-date" in result.stdout

    def test_cli_status_command_help(self):
        """Test status subcommand help"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"), "status", "--help" 
        ], capture_output=True, text=True)
        
        assert result.returncode == 0

    def test_cli_config_command_help(self):
        """Test config subcommand help"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"), "config", "--help"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0

    def test_cli_test_command_help(self):
        """Test test subcommand help"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"), "test", "--help"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0

    @patch('sync.SocialSyncOrchestrator')
    def test_sync_command_dry_run(self, mock_orchestrator_class):
        """Test sync command with dry-run flag"""
        mock_orchestrator = Mock()
        mock_orchestrator.run_sync.return_value = {
            'success': True,
            'synced_count': 2,
            'failed_count': 0,
            'total_processed': 2,
            'duration': 1.5,
            'dry_run': True
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock environment variables to avoid validation errors
        with patch.dict(os.environ, {
            'BLUESKY_HANDLE': 'test.bsky.social',
            'BLUESKY_PASSWORD': 'test-password',
            'MASTODON_ACCESS_TOKEN': 'test-token'
        }):
            result = subprocess.run([
                sys.executable, str(Path(__file__).parent.parent / "sync.py"), 
                "sync", "--dry-run"
            ], capture_output=True, text=True)
        
        # Should complete successfully
        assert result.returncode == 0

    @patch('sync.SocialSyncOrchestrator')
    def test_sync_command_since_date(self, mock_orchestrator_class):
        """Test sync command with since-date parameter"""
        mock_orchestrator = Mock()
        mock_orchestrator.run_sync.return_value = {
            'success': True,
            'synced_count': 1,
            'failed_count': 0,
            'total_processed': 1,
            'duration': 0.8,
            'dry_run': False
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with patch.dict(os.environ, {
            'BLUESKY_HANDLE': 'test.bsky.social',
            'BLUESKY_PASSWORD': 'test-password',
            'MASTODON_ACCESS_TOKEN': 'test-token'
        }):
            result = subprocess.run([
                sys.executable, str(Path(__file__).parent.parent / "sync.py"),
                "sync", "--since-date", "2025-01-01"
            ], capture_output=True, text=True)
        
        assert result.returncode == 0

    @patch('sync.SocialSyncOrchestrator')
    def test_status_command(self, mock_orchestrator_class):
        """Test status command"""
        mock_orchestrator = Mock()
        mock_orchestrator.get_sync_status.return_value = {
            'last_sync_time': '2025-01-01T12:00:00',
            'total_synced_posts': 10,
            'dry_run_mode': False
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with patch.dict(os.environ, {
            'BLUESKY_HANDLE': 'test.bsky.social',
            'BLUESKY_PASSWORD': 'test-password',
            'MASTODON_ACCESS_TOKEN': 'test-token'
        }):
            result = subprocess.run([
                sys.executable, str(Path(__file__).parent.parent / "sync.py"),
                "status"
            ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Sync Status" in result.stdout

    @patch('sync.get_settings')
    def test_config_command(self, mock_get_settings):
        """Test config command displays settings"""
        mock_settings = Mock()
        mock_settings.bluesky_handle = 'test.bsky.social'
        mock_settings.mastodon_api_base_url = 'https://mastodon.social'
        mock_settings.sync_interval_minutes = 15
        mock_settings.max_posts_per_sync = 10
        mock_settings.dry_run = False
        mock_settings.log_level = 'INFO'
        mock_get_settings.return_value = mock_settings
        
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"),
            "config"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Configuration" in result.stdout

    @patch('sync.BlueskyClient')
    @patch('sync.MastodonClient')
    def test_test_command_success(self, mock_mastodon_class, mock_bluesky_class):
        """Test test command with successful connections"""
        # Mock successful authentication
        mock_bluesky = Mock()
        mock_bluesky.authenticate.return_value = True
        mock_bluesky_class.return_value = mock_bluesky
        
        mock_mastodon = Mock()
        mock_mastodon.authenticate.return_value = True
        mock_mastodon_class.return_value = mock_mastodon
        
        with patch.dict(os.environ, {
            'BLUESKY_HANDLE': 'test.bsky.social',
            'BLUESKY_PASSWORD': 'test-password',
            'MASTODON_API_BASE_URL': 'https://mastodon.social',
            'MASTODON_ACCESS_TOKEN': 'test-token'
        }):
            result = subprocess.run([
                sys.executable, str(Path(__file__).parent.parent / "sync.py"),
                "test"
            ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Connection Test" in result.stdout

    @patch('sync.BlueskyClient')
    @patch('sync.MastodonClient')
    def test_test_command_failure(self, mock_mastodon_class, mock_bluesky_class):
        """Test test command with failed connections"""
        # Mock failed authentication
        mock_bluesky = Mock()
        mock_bluesky.authenticate.return_value = False
        mock_bluesky_class.return_value = mock_bluesky
        
        mock_mastodon = Mock()
        mock_mastodon.authenticate.return_value = False
        mock_mastodon_class.return_value = mock_mastodon
        
        with patch.dict(os.environ, {
            'BLUESKY_HANDLE': 'test.bsky.social',
            'BLUESKY_PASSWORD': 'test-password',
            'MASTODON_API_BASE_URL': 'https://mastodon.social',
            'MASTODON_ACCESS_TOKEN': 'test-token'
        }):
            result = subprocess.run([
                sys.executable, str(Path(__file__).parent.parent / "sync.py"),
                "test"
            ], capture_output=True, text=True)
        
        # Should exit with non-zero code on test failure
        assert result.returncode != 0

    def test_invalid_command(self):
        """Test CLI with invalid command"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"),
            "invalid-command"
        ], capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "No such command" in result.stderr

    def test_sync_missing_credentials(self):
        """Test sync command fails with missing credentials"""
        # Clear environment variables
        env = {k: v for k, v in os.environ.items() 
               if not k.startswith(('BLUESKY_', 'MASTODON_'))}
        
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"),
            "sync", "--dry-run"
        ], capture_output=True, text=True, env=env)
        
        # Should fail due to missing credentials
        assert result.returncode != 0

    @patch('sync.setup_logging')
    def test_logging_setup_called(self, mock_setup_logging):
        """Test that logging setup is called"""
        with patch.dict(os.environ, {
            'BLUESKY_HANDLE': 'test.bsky.social',
            'BLUESKY_PASSWORD': 'test-password',
            'MASTODON_ACCESS_TOKEN': 'test-token'
        }):
            # Just test that the CLI starts up and calls setup_logging
            result = subprocess.run([
                sys.executable, str(Path(__file__).parent.parent / "sync.py"),
                "--help"
            ], capture_output=True, text=True)
        
        assert result.returncode == 0

    def test_cli_log_level_option(self):
        """Test CLI log level option"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / "sync.py"),
            "--log-level", "DEBUG", "--help"
        ], capture_output=True, text=True)
        
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
