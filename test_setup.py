#!/usr/bin/env python3
"""
Test script for Social Sync - validates setup and configuration
"""
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required packages can be imported"""
    logger.info("Testing package imports...")
    
    try:
        import atproto
        logger.info("✅ atproto package imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import atproto: {e}")
        return False
    
    try:
        import mastodon
        logger.info("✅ mastodon package imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import mastodon: {e}")
        return False
    
    try:
        from src.config import get_settings
        logger.info("✅ config module imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import config: {e}")
        return False
    
    return True

def test_configuration():
    """Test configuration loading"""
    logger.info("Testing configuration...")
    
    try:
        from src.config import get_settings
        
        # Try to load settings
        settings = get_settings()
        logger.info("✅ Configuration loaded successfully")
        
        # Check if example values are still being used
        if settings.bluesky_handle == "your-handle.bsky.social":
            logger.warning("⚠️  Bluesky handle is still set to example value")
            return False
        
        if settings.bluesky_password == "your-app-password":
            logger.warning("⚠️  Bluesky password is still set to example value")
            return False
        
        if settings.mastodon_access_token == "your-access-token":
            logger.warning("⚠️  Mastodon access token is still set to example value")
            return False
        
        logger.info(f"✅ Bluesky handle: {settings.bluesky_handle}")
        logger.info(f"✅ Mastodon instance: {settings.mastodon_api_base_url}")
        logger.info(f"✅ Configuration validated")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        return False

def test_client_connections():
    """Test client authentication"""
    logger.info("Testing client connections...")
    
    try:
        from src.bluesky_client import BlueskyClient
        from src.mastodon_client import MastodonClient
        from src.config import get_settings
        
        settings = get_settings()
        
        # Test Bluesky client
        logger.info("Testing Bluesky connection...")
        bluesky_client = BlueskyClient(
            handle=settings.bluesky_handle,
            password=settings.bluesky_password
        )
        
        if bluesky_client.authenticate():
            logger.info("✅ Bluesky authentication successful")
        else:
            logger.error("❌ Bluesky authentication failed")
            return False
        
        # Test Mastodon client
        logger.info("Testing Mastodon connection...")
        mastodon_client = MastodonClient(
            api_base_url=settings.mastodon_api_base_url,
            access_token=settings.mastodon_access_token
        )
        
        if mastodon_client.authenticate():
            logger.info("✅ Mastodon authentication successful")
        else:
            logger.error("❌ Mastodon authentication failed")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Client connection error: {e}")
        return False

def test_sync_functionality():
    """Test basic sync functionality"""
    logger.info("Testing sync functionality...")
    
    try:
        from src.sync_orchestrator import SocialSyncOrchestrator
        
        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()
        
        # Test setup clients
        if not orchestrator.setup_clients():
            logger.error("❌ Failed to setup clients")
            return False
        
        logger.info("✅ Client setup successful")
        
        # Test getting posts (don't actually sync)
        posts_to_sync = orchestrator.get_posts_to_sync()
        logger.info(f"✅ Found {len(posts_to_sync)} posts to potentially sync")
        
        # Test sync status
        status = orchestrator.get_sync_status()
        logger.info(f"✅ Sync status retrieved: {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Sync functionality error: {e}")
        return False

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
            results[test_name] = test_func()
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
