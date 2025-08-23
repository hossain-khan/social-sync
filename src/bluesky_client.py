"""
Bluesky client wrapper for Social Sync
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from atproto import Client as AtprotoClient, models
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class BlueskyPost:
    """Represents a Bluesky post with metadata"""
    uri: str
    cid: str
    text: str
    created_at: datetime
    author_handle: str
    author_display_name: Optional[str] = None
    reply_to: Optional[str] = None
    embed: Optional[Dict[str, Any]] = None


class BlueskyClient:
    """Wrapper for Bluesky AT Protocol client"""
    
    def __init__(self, handle: str, password: str):
        self.handle = handle
        self.password = password
        self.client = AtprotoClient()
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with Bluesky"""
        try:
            profile = self.client.login(self.handle, self.password)
            self._authenticated = True
            logger.info(f"Successfully authenticated as {profile.display_name} (@{profile.handle})")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Bluesky: {e}")
            return False
    
    def get_recent_posts(self, limit: int = 10) -> List[BlueskyPost]:
        """Get recent posts from authenticated user's feed"""
        if not self._authenticated:
            raise RuntimeError("Client not authenticated. Call authenticate() first.")
        
        try:
            # Get the user's own posts
            response = self.client.get_author_feed(
                actor=self.handle,
                limit=limit
            )
            
            posts = []
            for feed_item in response.feed:
                post = feed_item.post
                
                # Skip reposts and replies for now
                if hasattr(feed_item, 'reason') or post.record.reply:
                    continue
                
                bluesky_post = BlueskyPost(
                    uri=post.uri,
                    cid=post.cid,
                    text=post.record.text,
                    created_at=datetime.fromisoformat(post.record.created_at.replace('Z', '+00:00')),
                    author_handle=post.author.handle,
                    author_display_name=post.author.display_name,
                    reply_to=post.record.reply.parent.uri if post.record.reply else None,
                    embed=post.record.embed.py_object if hasattr(post.record, 'embed') and post.record.embed else None
                )
                posts.append(bluesky_post)
            
            logger.info(f"Retrieved {len(posts)} posts from Bluesky")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to fetch posts from Bluesky: {e}")
            return []
    
    def get_post_thread(self, post_uri: str) -> Optional[Dict[str, Any]]:
        """Get post thread context"""
        try:
            response = self.client.get_post_thread(uri=post_uri)
            return response.thread
        except Exception as e:
            logger.error(f"Failed to fetch post thread: {e}")
            return None
