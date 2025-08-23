"""
Mastodon client wrapper for Social Sync
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from mastodon import Mastodon

logger = logging.getLogger(__name__)


@dataclass
class MastodonPost:
    """Represents a Mastodon post with metadata"""

    id: str
    content: str
    created_at: datetime
    url: str
    in_reply_to_id: Optional[str] = None
    media_attachments: Optional[List[Dict[str, Any]]] = None


class MastodonClient:
    """Wrapper for Mastodon API client"""

    def __init__(self, api_base_url: str, access_token: str):
        self.api_base_url = api_base_url
        self.access_token = access_token
        self.client: Optional[Mastodon] = None
        self._authenticated = False

    def authenticate(self) -> bool:
        """Initialize Mastodon client"""
        try:
            self.client = Mastodon(
                access_token=self.access_token, api_base_url=self.api_base_url
            )

            # Verify credentials
            if self.client:
                account = self.client.me()
                self._authenticated = True
                logger.info(f"Successfully connected to Mastodon as @{account['username']}")
                return True
            else:
                logger.error("Failed to initialize Mastodon client")
                return False

        except Exception as e:
            logger.error(f"Failed to authenticate with Mastodon: {e}")
            return False

    def post_status(
        self,
        text: str,
        in_reply_to_id: Optional[str] = None,
        media_ids: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Post a status to Mastodon"""
        if not self._authenticated or not self.client:
            raise RuntimeError("Client not authenticated. Call authenticate() first.")

        try:
            status = self.client.status_post(
                status=text, in_reply_to_id=in_reply_to_id, media_ids=media_ids
            )

            logger.info(f"Successfully posted status to Mastodon: {status['id']}")
            return status if isinstance(status, dict) else None

        except Exception as e:
            logger.error(f"Failed to post status to Mastodon: {e}")
            return None

    def upload_media(
        self, media_file: bytes, mime_type: Optional[str] = None, description: Optional[str] = None
    ) -> Optional[str]:
        """Upload media to Mastodon"""
        if not self._authenticated or not self.client:
            raise RuntimeError("Client not authenticated. Call authenticate() first.")

        try:
            media = self.client.media_post(
                media_file=media_file, mime_type=mime_type, description=description
            )

            logger.info(f"Successfully uploaded media to Mastodon: {media['id']}")
            return media["id"] if isinstance(media, dict) and "id" in media else None

        except Exception as e:
            logger.error(f"Failed to upload media to Mastodon: {e}")
            return None

    def get_recent_posts(self, limit: int = 10) -> List[MastodonPost]:
        """Get recent posts from authenticated user"""
        if not self._authenticated or not self.client:
            raise RuntimeError("Client not authenticated. Call authenticate() first.")

        try:
            account = self.client.me()
            statuses = self.client.account_statuses(id=account["id"], limit=limit)

            posts = []
            for status in statuses:
                mastodon_post = MastodonPost(
                    id=status["id"],
                    content=status["content"],
                    created_at=status["created_at"],
                    url=status["url"],
                    in_reply_to_id=status["in_reply_to_id"],
                    media_attachments=status["media_attachments"] or [],
                )
                posts.append(mastodon_post)

            logger.info(f"Retrieved {len(posts)} posts from Mastodon")
            return posts

        except Exception as e:
            logger.error(f"Failed to fetch posts from Mastodon: {e}")
            return []
