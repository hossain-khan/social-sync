#!/usr/bin/env python3
"""
Social Sync CLI - Command line interface for syncing social media posts
"""

import logging
import os
import subprocess  # nosec B404
import sys
import warnings
from pathlib import Path

# Suppress urllib3 OpenSSL warning on macOS (LibreSSL is functionally equivalent)
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")

import click
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import ConfigurationError, get_settings  # noqa: E402
from src.sync_orchestrator import SocialSyncOrchestrator  # noqa: E402

try:
    from src.social_sync import __version__
except ImportError:
    __version__ = "unknown"

# Template used by the `setup` command — embedded so it works in standalone binaries
# (no dependency on .env.example being present on disk)
ENV_TEMPLATE = """\
# Environment variables for Social Sync
# Fill in your credentials below

# Bluesky Credentials
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password

# Mastodon Credentials
MASTODON_API_BASE_URL=https://mastodon.social
MASTODON_ACCESS_TOKEN=your-access-token

# Sync Configuration
SYNC_INTERVAL_MINUTES=60
MAX_POSTS_PER_SYNC=10
# Start date for syncing posts (ISO format). If not set, starts from 7 days ago
# Examples:
#   SYNC_START_DATE=2025-01-01
#   SYNC_START_DATE=2025-01-15T10:30:00
#   SYNC_START_DATE=2025-01-15T10:30:00-05:00
# SYNC_START_DATE=2025-01-01
# SYNC_CONTENT_WARNINGS=true
DRY_RUN=true
# DISABLE_SOURCE_PLATFORM=false

# Video Sync Settings
SYNC_VIDEOS=false
MAX_VIDEO_SIZE_MB=40

# Media Upload Failure Handling
IMAGE_UPLOAD_FAILURE_STRATEGY=partial
IMAGE_UPLOAD_MAX_RETRIES=3

# Logging
LOG_LEVEL=INFO
"""


def _cli_name() -> str:
    """Return the name to use in usage hints (binary name or 'python sync.py')."""
    if getattr(sys, "frozen", False):
        return Path(sys.argv[0]).name
    return "python sync.py"


# Load environment variables
load_dotenv()


def setup_logging(log_level: str):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("social_sync.log"),
        ],
    )


@click.group()
@click.version_option(version=__version__, prog_name="Social Sync")
@click.option(
    "--log-level",
    default="INFO",
    help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
@click.pass_context
def cli(ctx, log_level):
    """Social Sync - Sync posts from Bluesky to Mastodon"""
    ctx.ensure_object(dict)
    setup_logging(log_level)


@cli.command()
@click.option(
    "--dry-run", is_flag=True, help="Run without actually posting to Mastodon"
)
@click.option(
    "--since-date",
    help="Start date for syncing posts (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
)
@click.option(
    "--disable-source-platform",
    is_flag=True,
    help="Disable adding source platform attribution (e.g., 'via Bluesky 🦋') to synced posts",
)
def sync(dry_run, since_date, disable_source_platform):
    """Run the sync process"""
    if dry_run:
        os.environ["DRY_RUN"] = "true"

    if since_date:
        os.environ["SYNC_START_DATE"] = since_date

    if disable_source_platform:
        os.environ["DISABLE_SOURCE_PLATFORM"] = "true"

    try:
        orchestrator = SocialSyncOrchestrator()
        result = orchestrator.run_sync()

        if result["success"]:
            click.echo("✅ Sync completed successfully!")
            click.echo(f"   • Synced: {result['synced_count']} posts")
            if result["failed_count"] > 0:
                click.echo(f"   • Failed: {result['failed_count']} posts")
            if result.get("skipped_count", 0) > 0:
                click.echo(
                    f"   • Skipped: {result['skipped_count']} posts (with #no-sync tag)"
                )
            click.echo(f"   • Duration: {result['duration']:.2f}s")
            if result["dry_run"]:
                click.echo("   • Mode: DRY RUN (no posts actually created)")
        else:
            click.echo(f"❌ Sync failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except ConfigurationError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error during sync")
        click.echo(f"❌ Unexpected error: {e}")
        sys.exit(1)


@cli.command()
def status():
    """Show sync status"""
    try:
        orchestrator = SocialSyncOrchestrator()
        status_info = orchestrator.get_sync_status()

        click.echo("📊 Social Sync Status")
        click.echo(f"   • Last sync: {status_info['last_sync_time'] or 'Never'}")
        click.echo(f"   • Total synced posts: {status_info['total_synced_posts']}")
        click.echo(
            f"   • Dry run mode: {'ON' if status_info['dry_run_mode'] else 'OFF'}"
        )

    except ConfigurationError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Error getting status")
        click.echo(f"❌ Error getting status: {e}")
        sys.exit(1)


@cli.command()
def config():
    """Show current configuration"""
    try:
        settings = get_settings()

        click.echo("⚙️ Social Sync Configuration")
        click.echo(f"   • Bluesky handle: {settings.bluesky_handle}")
        click.echo(f"   • Mastodon instance: {settings.mastodon_api_base_url}")
        click.echo(f"   • Sync interval: {settings.sync_interval_minutes} minutes")
        click.echo(f"   • Max posts per sync: {settings.max_posts_per_sync}")

        # Show sync start date (either configured or default)
        sync_start = settings.get_sync_start_datetime()
        if settings.sync_start_date:
            click.echo(f"   • Sync start date: {settings.sync_start_date} (configured)")
        else:
            click.echo(
                f"   • Sync start date: {sync_start.strftime('%Y-%m-%d')} (default: 7 days ago)"
            )

        click.echo(f"   • Dry run: {settings.dry_run}")
        click.echo(f"   • Log level: {settings.log_level}")

    except ConfigurationError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error reading configuration: {e}")
        sys.exit(1)


@cli.command()
def setup():
    """Interactive setup wizard to configure Social Sync."""
    try:
        click.echo("🚀 Welcome to Social Sync Setup!\n")

        # Check if .env already exists
        env_path = Path(".env")
        if env_path.exists():
            if not click.confirm(
                "⚠️  .env file already exists. Do you want to overwrite it?"
            ):
                click.echo(
                    f"Setup cancelled. Use '{_cli_name()} config' to view current configuration."
                )
                return

        # Write the embedded template (works even in standalone binary — no .env.example needed)
        env_path.write_text(ENV_TEMPLATE)
        click.echo("✅ Created .env configuration file")

        cli = _cli_name()
        click.echo("\n📝 Next steps:")
        click.echo("1. Edit the .env file with your credentials:")
        click.echo("   - BLUESKY_HANDLE: Your Bluesky handle (e.g., user.bsky.social)")
        click.echo("   - BLUESKY_PASSWORD: Your Bluesky app password")
        click.echo("   - MASTODON_ACCESS_TOKEN: Your Mastodon access token")
        click.echo("   - MASTODON_API_BASE_URL: Your Mastodon instance URL")
        click.echo("\n2. Test your configuration:")
        click.echo(f"   {cli} test")
        click.echo("\n3. Run your first sync:")
        click.echo(f"   {cli} sync --dry-run")
        click.echo("\n📖 For detailed setup instructions, see:")
        click.echo(
            "   https://github.com/hossain-khan/social-sync/blob/main/docs/SETUP.md"
        )

        # Offer to open the file for editing
        if click.confirm("\n🔧 Would you like to open .env for editing now?"):
            editor = os.environ.get("EDITOR", "nano")

            # Whitelist of safe editors to prevent command injection
            safe_editors = ["nano", "vim", "vi", "emacs", "code", "notepad"]
            editor_cmd = editor.split()[0]  # Get just the command name, not args

            if editor_cmd in safe_editors:
                click.echo(f"Opening .env with {editor}...")
                try:
                    subprocess.run([editor_cmd, ".env"], check=True)  # nosec B603
                except subprocess.CalledProcessError:
                    click.echo(
                        f"⚠️  Could not open {editor_cmd}. Please edit .env manually."
                    )
                except FileNotFoundError:
                    click.echo(
                        f"⚠️  Editor '{editor_cmd}' not found. Please edit .env manually."
                    )
            else:
                click.echo(
                    f"⚠️  Editor '{editor_cmd}' not in safe list. Please edit .env manually."
                )

    except Exception as e:
        click.echo(f"❌ Error during setup: {e}", err=True)
        sys.exit(1)


@cli.command()
def test():
    """Test client connections without syncing"""
    try:
        orchestrator = SocialSyncOrchestrator()

        click.echo("🔧 Testing client connections...")

        if orchestrator.setup_clients():
            click.echo("✅ All clients authenticated successfully!")
        else:
            click.echo("❌ Client authentication failed!")
            sys.exit(1)

    except ConfigurationError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logging.exception("Error testing connections")
        click.echo(f"❌ Error testing connections: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
