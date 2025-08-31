#!/usr/bin/env python3
"""
Test script for Social Sync - validates setup and configuration
"""
import os  # noqa: F401
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def is_ci_environment():
    """Check if running in CI environment"""
    return os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("CI") == "true"


def has_valid_credentials():
    """Check if valid credentials are available"""
    # Check for real credentials (not test/example values)
    bluesky_handle = os.getenv("BLUESKY_HANDLE", "")
    bluesky_password = os.getenv("BLUESKY_PASSWORD", "")
    mastodon_token = os.getenv("MASTODON_ACCESS_TOKEN", "")

    # Skip if using test/example credentials or empty values
    test_values = [
        "",
        "your-handle.bsky.social",
        "your-app-password",
        "your-access-token",
        "test.bsky.social",
        "test-password",
        "test-token-12345",
    ]

    if (
        bluesky_handle in test_values
        or bluesky_password in test_values
        or mastodon_token in test_values
    ):
        return False

    return bool(bluesky_handle and bluesky_password and mastodon_token)


def test_imports():
    """Test that all required packages can be imported"""
    logger.info("Testing package imports...")

    # Test atproto import
    try:
        import atproto  # noqa: F401

        logger.info("✅ atproto package imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import atproto: {e}")
        assert False, f"Failed to import atproto: {e}"

    # Test mastodon import
    try:
        import mastodon  # noqa: F401

        logger.info("✅ mastodon package imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import mastodon: {e}")
        assert False, f"Failed to import mastodon: {e}"

    # Test config import
    try:
        from src.config import get_settings  # noqa: F401

        logger.info("✅ config module imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import config: {e}")
        assert False, f"Failed to import config: {e}"


def test_configuration():
    """Test configuration loading"""
    logger.info("Testing configuration...")

    # Skip test if in CI environment or no valid credentials
    if is_ci_environment() or not has_valid_credentials():
        pytest.skip(
            "Skipping configuration test - no valid credentials available in CI environment"
        )

    try:
        from src.config import get_settings

        # Try to load settings
        settings = get_settings()
        logger.info("✅ Configuration loaded successfully")

        # Check if example values are still being used
        assert (
            settings.bluesky_handle != "your-handle.bsky.social"
        ), "Bluesky handle is still set to example value"

        assert (
            settings.bluesky_password != "your-app-password"
        ), "Bluesky password is still set to example value"

        assert (
            settings.mastodon_access_token != "your-access-token"
        ), "Mastodon access token is still set to example value"

        logger.info(f"✅ Bluesky handle: {settings.bluesky_handle}")
        logger.info(f"✅ Mastodon instance: {settings.mastodon_api_base_url}")
        logger.info("✅ Configuration validated")

    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        assert False, f"Configuration error: {e}"


def test_client_connections():
    """Test client authentication"""
    logger.info("Testing client connections...")

    # Skip test if in CI environment or no valid credentials
    if is_ci_environment() or not has_valid_credentials():
        pytest.skip(
            "Skipping client connection test - no valid credentials available in CI environment"
        )

    try:
        from src.bluesky_client import BlueskyClient
        from src.config import get_settings
        from src.mastodon_client import MastodonClient

        settings = get_settings()

        # Test Bluesky client
        logger.info("Testing Bluesky connection...")
        bluesky_client = BlueskyClient(
            handle=settings.bluesky_handle, password=settings.bluesky_password
        )

        bluesky_auth_result = bluesky_client.authenticate()
        if bluesky_auth_result:
            logger.info("✅ Bluesky authentication successful")
        else:
            logger.error("❌ Bluesky authentication failed")
            assert False, "Bluesky authentication failed"

        # Test Mastodon client
        logger.info("Testing Mastodon connection...")
        mastodon_client = MastodonClient(
            api_base_url=settings.mastodon_api_base_url,
            access_token=settings.mastodon_access_token,
        )

        mastodon_auth_result = mastodon_client.authenticate()
        if mastodon_auth_result:
            logger.info("✅ Mastodon authentication successful")
        else:
            logger.error("❌ Mastodon authentication failed")
            assert False, "Mastodon authentication failed"

    except Exception as e:
        logger.error(f"❌ Client connection error: {e}")
        assert False, f"Client connection error: {e}"


def test_sync_functionality():
    """Test basic sync functionality"""
    logger.info("Testing sync functionality...")

    # Skip test if in CI environment or no valid credentials
    if is_ci_environment() or not has_valid_credentials():
        pytest.skip(
            "Skipping sync functionality test - no valid credentials available in CI environment"
        )

    try:
        from src.sync_orchestrator import SocialSyncOrchestrator

        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()

        # Test setup clients
        client_setup_result = orchestrator.setup_clients()
        if not client_setup_result:
            logger.error("❌ Failed to setup clients")
            assert False, "Failed to setup clients"

        logger.info("✅ Client setup successful")

        # Test getting posts (don't actually sync)
        posts_to_sync = orchestrator.get_posts_to_sync()
        logger.info(f"✅ Found {len(posts_to_sync)} posts to potentially sync")

        # Test sync status
        status = orchestrator.get_sync_status()
        logger.info(f"✅ Sync status retrieved: {status}")

        # Ensure we get a valid status response
        assert status is not None, "Sync status should not be None"

    except Exception as e:
        logger.error(f"❌ Sync functionality error: {e}")
        assert False, f"Sync functionality error: {e}"


def main():
    """Run all tests"""
    logger.info("🧪 Running Social Sync Tests\n")

    tests = [
        ("Package Imports", test_imports),
        ("Configuration", test_configuration),
        ("Client Connections", test_client_connections),
        ("Sync Functionality", test_sync_functionality),
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info(f"📋 {test_name}")
        try:
            test_func()
            results[test_name] = True
            logger.info("✅ Test passed")
        except AssertionError as e:
            logger.error(f"❌ Test assertion failed: {e}")
            results[test_name] = False
        except Exception as e:
            logger.error(f"❌ Unexpected error in {test_name}: {e}")
            results[test_name] = False
        logger.info("")

    # Summary
    logger.info("📊 Test Results Summary:")
    all_passed = True

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 All tests passed! Social Sync is ready to use.")
        return 0
    else:
        logger.error("\n💥 Some tests failed. Please check your configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
