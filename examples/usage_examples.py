#!/usr/bin/env python3
"""
Example script demonstrating Social Sync components
"""
import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
from dotenv import load_dotenv

from src.config import get_settings
from src.bluesky_client import BlueskyClient
from src.mastodon_client import MastodonClient
from src.content_processor import ContentProcessor
from src.sync_state import SyncState

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def example_basic_usage():
    """Example: Basic sync workflow"""
    logger.info("=== Basic Usage Example ===")
    
    # Load settings
    settings = get_settings()
    
    # Initialize clients
    bluesky = BlueskyClient(settings.bluesky_handle, settings.bluesky_password)
    mastodon = MastodonClient(settings.mastodon_api_base_url, settings.mastodon_access_token)
    
    # Authenticate
    if not bluesky.authenticate():
        logger.error("Bluesky authentication failed")
        return
    
    if not mastodon.authenticate():
        logger.error("Mastodon authentication failed")  
        return
    
    # Get recent posts
    posts = bluesky.get_recent_posts(limit=5)
    logger.info(f"Retrieved {len(posts)} recent posts from Bluesky")
    
    # Process and display first post
    if posts:
        post = posts[0]
        logger.info(f"Latest post: {post.text[:100]}...")
        
        # Process content for Mastodon
        processor = ContentProcessor()
        processed_text = processor.process_bluesky_to_mastodon(post.text, post.embed)
        logger.info(f"Processed for Mastodon: {processed_text[:100]}...")

def example_content_processing():
    """Example: Content processing features"""
    logger.info("=== Content Processing Example ===")
    
    processor = ContentProcessor()
    
    # Test different content types
    test_cases = [
        "Simple text post without any special content",
        "Post with #hashtags and @mentions.bsky.social",
        "Long post that exceeds the character limit " + "x" * 500,
        "Post with a link: https://example.com/article"
    ]
    
    for i, text in enumerate(test_cases, 1):
        logger.info(f"\n--- Test Case {i} ---")
        logger.info(f"Original: {text}")
        
        processed = processor.process_bluesky_to_mastodon(text)
        logger.info(f"Processed: {processed}")
        
        # Show statistics
        logger.info(f"Length: {len(processed)} chars")
        hashtags = processor.extract_hashtags(processed)
        mentions = processor.extract_mentions(processed)
        urls = processor.extract_urls(processed)
        
        if hashtags:
            logger.info(f"Hashtags: {hashtags}")
        if mentions:
            logger.info(f"Mentions: {mentions}")
        if urls:
            logger.info(f"URLs: {urls}")

def example_state_management():
    """Example: State management features"""
    logger.info("=== State Management Example ===")
    
    state = SyncState("example_state.json")
    
    # Show current state
    logger.info(f"Last sync time: {state.get_last_sync_time()}")
    logger.info(f"Synced posts count: {state.get_synced_posts_count()}")
    
    # Simulate marking posts as synced
    example_uris = [
        "at://did:plc:abc123/app.bsky.feed.post/example1",
        "at://did:plc:abc123/app.bsky.feed.post/example2"
    ]
    
    for uri in example_uris:
        if not state.is_post_synced(uri):
            state.mark_post_synced(uri, f"mastodon_id_{len(uri) % 1000}")
            logger.info(f"Marked as synced: {uri}")
        else:
            logger.info(f"Already synced: {uri}")
    
    # Update sync time
    state.update_sync_time()
    logger.info("Updated sync time")
    
    # Show updated state
    logger.info(f"New synced posts count: {state.get_synced_posts_count()}")

def example_dry_run_sync():
    """Example: Dry run sync process"""
    logger.info("=== Dry Run Sync Example ===")
    
    try:
        from src.sync_orchestrator import SocialSyncOrchestrator
        
        # Create orchestrator
        orchestrator = SocialSyncOrchestrator()
        
        # Override dry run setting
        orchestrator.settings.dry_run = True
        
        # Run sync
        result = orchestrator.run_sync()
        
        # Display results
        logger.info("Sync Results:")
        for key, value in result.items():
            logger.info(f"  {key}: {value}")
            
    except Exception as e:
        logger.error(f"Sync error: {e}")

def example_configuration_validation():
    """Example: Configuration validation"""
    logger.info("=== Configuration Validation Example ===")
    
    try:
        settings = get_settings()
        
        logger.info("Current Configuration:")
        logger.info(f"  Bluesky Handle: {settings.bluesky_handle}")
        logger.info(f"  Mastodon Instance: {settings.mastodon_api_base_url}")
        logger.info(f"  Max Posts Per Sync: {settings.max_posts_per_sync}")
        logger.info(f"  Dry Run Mode: {settings.dry_run}")
        logger.info(f"  Log Level: {settings.log_level}")
        
        # Validate settings
        if settings.bluesky_handle != "your-handle.bsky.social":
            logger.info("✅ Bluesky handle is configured")
        else:
            logger.warning("⚠️  Bluesky handle needs to be configured")
            
        if settings.mastodon_access_token != "your-access-token":
            logger.info("✅ Mastodon token is configured")
        else:
            logger.warning("⚠️  Mastodon token needs to be configured")
            
    except Exception as e:
        logger.error(f"Configuration error: {e}")

def main():
    """Run all examples"""
    logger.info("🚀 Social Sync Examples\n")
    
    examples = [
        ("Configuration Validation", example_configuration_validation),
        ("Content Processing", example_content_processing),
        ("State Management", example_state_management),
        ("Basic Usage", example_basic_usage),
        ("Dry Run Sync", example_dry_run_sync),
    ]
    
    for name, example_func in examples:
        try:
            logger.info(f"\n{'='*50}")
            example_func()
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
        
        logger.info(f"{'='*50}\n")
    
    logger.info("✅ All examples completed!")

if __name__ == "__main__":
    main()
