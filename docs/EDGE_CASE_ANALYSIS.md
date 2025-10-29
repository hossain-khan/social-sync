# Edge Case Analysis: Bluesky AT Protocol & Mastodon API Integration

**Date**: 2025-10-29  
**Scope**: Cross-platform post synchronization between Bluesky and Mastodon  
**Purpose**: Comprehensive analysis of potential edge cases not yet covered in the implementation

---

## Executive Summary

This document provides a detailed analysis of edge cases discovered through examination of:
- Bluesky AT Protocol API specifications
- Mastodon API v1 specifications
- Current implementation in `src/sync_orchestrator.py`, `src/bluesky_client.py`, `src/mastodon_client.py`, and `src/content_processor.py`
- Recent bug fixes documented in CHANGELOG.md (versions 0.2.0 - 0.6.0)

**Recent Bugs Fixed** (context):
- v0.6.0: recordWithMedia image sync failure (quoted posts with images)
- v0.5.0: Nested reply detection in threads started by others
- v0.3.0: Image attachment blob reference extraction
- v0.2.0: Duplicate link handling with facets and external embeds

---

## Critical Edge Cases (High Priority)

### 1. Bluesky Text Encoding and Multi-byte Characters

**Category**: Content Processing  
**Severity**: HIGH  
**Current Status**: ⚠️ PARTIALLY HANDLED

**Issue**:
The current implementation in `ContentProcessor._expand_urls_from_facets()` has a comment acknowledging multi-byte character handling issues:

```python
# Note: This assumes UTF-8 encoding where most characters are 1 byte
# For more accurate conversion, we'd need to properly handle multi-byte chars
```

**Impact**:
- Facets use byte positions (byteStart, byteEnd) not character positions
- Emoji, CJK characters, and other multi-byte UTF-8 characters can cause incorrect URL expansion
- Links may be misaligned or truncated in posts with emoji/international characters
- Could result in malformed URLs or text corruption

**Example Scenario**:
```
Post text: "🎉 Check out https://example.com..."
Facet byteStart: 7, byteEnd: 35
Problem: "🎉" is 4 bytes, not 1 character
Result: URL expansion may extract wrong substring
```

**Fix Instructions**:

1. **Update `_expand_urls_from_facets()` method in `src/content_processor.py`**:
   - Replace the current byte-to-character conversion with proper UTF-8 handling
   - Use `text.encode('utf-8')` and slice at byte boundaries
   - Decode only after extracting the correct byte ranges

2. **Implementation approach**:
```python
@staticmethod
def _expand_urls_from_facets(text: str, facets: List[Dict[str, Any]]) -> str:
    """Expand truncated URLs using facets data from Bluesky
    
    Properly handles multi-byte UTF-8 characters in byte position calculations.
    """
    if not facets:
        return text
    
    # Convert text to bytes for accurate indexing
    text_bytes = text.encode('utf-8')
    
    # Process facets in reverse order to avoid index shifting
    sorted_facets = sorted(
        facets, 
        key=lambda f: f.get("index", {}).get("byteStart", 0), 
        reverse=True
    )
    
    for facet in sorted_facets:
        try:
            facet_index = facet.get("index", {})
            byte_start = facet_index.get("byteStart")
            byte_end = facet_index.get("byteEnd")
            
            if byte_start is None or byte_end is None:
                continue
            
            # Validate byte positions
            if byte_start < 0 or byte_end > len(text_bytes) or byte_start >= byte_end:
                logger.warning(f"Invalid facet byte range: {byte_start}-{byte_end}")
                continue
            
            features = facet.get("features", [])
            for feature in features:
                feature_type = feature.get("$type", "") or feature.get("py_type", "")
                if (feature_type.endswith("Link") or 
                    feature_type == "app.bsky.richtext.facet#link"):
                    full_url = feature.get("uri")
                    if full_url:
                        # Extract and replace at byte boundaries
                        before = text_bytes[:byte_start]
                        after = text_bytes[byte_end:]
                        
                        # Reconstruct with full URL
                        text_bytes = before + full_url.encode('utf-8') + after
                        logger.debug(f"Expanded URL from facets: {full_url}")
                        
        except Exception as e:
            logger.warning(f"Error processing facet for URL expansion: {e}")
            continue
    
    # Decode back to string
    return text_bytes.decode('utf-8', errors='replace')
```

3. **Add comprehensive tests** in `tests/test_content_processor_additional.py`:
   - Test with emoji before/after URLs
   - Test with CJK characters (Chinese, Japanese, Korean)
   - Test with mixed scripts and combining characters
   - Test edge case of facet at byte 0 with multi-byte prefix

4. **Validation**:
   - Run test suite to ensure no regressions
   - Test with real Bluesky posts containing emoji and international characters
   - Verify URL expansion accuracy across different character sets

---

### 2. Mastodon Instance-Specific Character Limits

**Category**: API Integration  
**Severity**: MEDIUM-HIGH  
**Current Status**: ⚠️ NOT HANDLED

**Issue**:
The current implementation uses a hardcoded `MASTODON_CHAR_LIMIT = 500` in `ContentProcessor`, but Mastodon instances can configure custom character limits (some allow 5000+ characters).

**Impact**:
- Unnecessary truncation on instances with higher limits
- Loss of content when syncing to more permissive instances
- Suboptimal user experience

**Current Code**:
```python
# content_processor.py
class ContentProcessor:
    MASTODON_CHAR_LIMIT = 500  # Hardcoded assumption
```

**Fix Instructions**:

1. **Add instance configuration detection** in `src/mastodon_client.py`:

```python
class MastodonClient:
    def __init__(self, api_base_url: str, access_token: str):
        self.api_base_url = api_base_url
        self.access_token = access_token
        self.client: Optional[Mastodon] = None
        self._authenticated = False
        self._instance_info: Optional[Dict[str, Any]] = None
        self._max_toot_chars: int = 500  # Default fallback
    
    def authenticate(self) -> bool:
        """Initialize Mastodon client and fetch instance configuration"""
        try:
            self.client = Mastodon(
                access_token=self.access_token, 
                api_base_url=self.api_base_url
            )
            
            if self.client:
                account = self.client.me()
                
                # Fetch instance information to get character limit
                try:
                    self._instance_info = self.client.instance()
                    # Instance info includes 'max_toot_chars' or 'configuration.statuses.max_characters'
                    if self._instance_info:
                        # Try new API format first
                        if 'configuration' in self._instance_info:
                            config = self._instance_info['configuration']
                            if 'statuses' in config:
                                self._max_toot_chars = config['statuses'].get('max_characters', 500)
                        # Fallback to older format
                        elif 'max_toot_chars' in self._instance_info:
                            self._max_toot_chars = self._instance_info['max_toot_chars']
                        
                        logger.info(f"Mastodon instance character limit: {self._max_toot_chars}")
                except Exception as e:
                    logger.warning(f"Could not fetch instance info, using default limit: {e}")
                
                self._authenticated = True
                logger.info(f"Successfully connected to Mastodon as @{account['username']}")
                return True
            else:
                logger.error("Failed to initialize Mastodon client")
                return False
        except Exception as e:
            logger.error(f"Failed to authenticate with Mastodon: {e}")
            return False
    
    def get_max_toot_chars(self) -> int:
        """Get the instance's maximum character limit for posts"""
        return self._max_toot_chars
```

2. **Update `ContentProcessor` to accept dynamic limit**:

```python
class ContentProcessor:
    # Remove hardcoded constant, use method parameter instead
    
    @staticmethod
    def _truncate_if_needed(text: str, char_limit: int = 500) -> str:
        """Truncate text if it exceeds the specified character limit"""
        if len(text) <= char_limit:
            return text
        
        # Try to truncate at a word boundary
        truncated = text[:char_limit - 3]
        last_space = truncated.rfind(" ")
        
        if last_space > char_limit * 0.8:
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    @staticmethod
    def process_bluesky_to_mastodon(
        text: str,
        embed: Optional[Dict[str, Any]] = None,
        facets: Optional[List[Dict[str, Any]]] = None,
        include_image_placeholders: bool = True,
        include_sync_attribution: bool = False,
        mastodon_char_limit: int = 500,  # New parameter
    ) -> str:
        """Process Bluesky post content for Mastodon compatibility"""
        processed_text = text
        
        # ... existing processing logic ...
        
        # Ensure we stay within the instance's character limit
        processed_text = ContentProcessor._truncate_if_needed(
            processed_text, 
            char_limit=mastodon_char_limit
        )
        
        return processed_text
```

3. **Update `SyncOrchestrator` to pass character limit**:

```python
def sync_post(self, bluesky_post: BlueskyPost) -> bool:
    """Sync a single post from Bluesky to Mastodon"""
    try:
        # ... existing code ...
        
        # Get the instance's character limit
        char_limit = self.mastodon_client.get_max_toot_chars()
        
        # Process content with instance-specific limit
        processed_text = self.content_processor.process_bluesky_to_mastodon(
            text=bluesky_post.text,
            embed=bluesky_post.embed,
            facets=bluesky_post.facets,
            include_image_placeholders=not has_images or self.settings.dry_run,
            mastodon_char_limit=char_limit,
        )
        
        # ... rest of existing code ...
```

4. **Add tests**:
   - Mock instance info response with various character limits
   - Test truncation behavior with different limits (500, 1000, 5000)
   - Test fallback to 500 when instance info unavailable

---

### 3. AT Protocol Self-Labels and Content Warnings

**Category**: Content Moderation  
**Severity**: MEDIUM  
**Current Status**: ❌ NOT HANDLED

**Issue**:
Bluesky posts can include self-labels (content warnings) such as:
- `"porn"` - Pornography
- `"nudity"` - Nudity
- `"graphic-media"` - Graphic violence/gore
- `"sexual"` - Sexual content

These labels are part of the AT Protocol post record but are not currently extracted or translated to Mastodon's Content Warning (CW) system.

**Impact**:
- NSFW content synced to Mastodon without appropriate warnings
- Potential TOS violations on Mastodon instances
- Users exposed to sensitive content without consent
- Moderation issues for public instances

**AT Protocol Structure**:
```python
# Post record includes:
{
    "text": "...",
    "labels": {
        "$type": "com.atproto.label.defs#selfLabels",
        "values": [
            {"val": "porn"},
            {"val": "graphic-media"}
        ]
    }
}
```

**Fix Instructions**:

1. **Update `BlueskyPost` dataclass** in `src/bluesky_client.py`:

```python
@dataclass
class BlueskyPost:
    uri: str
    cid: str
    text: str
    created_at: datetime
    author_handle: str
    author_display_name: Optional[str] = None
    reply_to: Optional[str] = None
    embed: Optional[Dict[str, Any]] = None
    facets: Optional[List[Dict[str, Any]]] = None
    self_labels: Optional[List[str]] = None  # NEW: List of self-label values
```

2. **Extract self-labels in `get_recent_posts()`**:

```python
def get_recent_posts(self, limit: int = 10, since_date: Optional[datetime] = None) -> BlueskyFetchResult:
    """Get recent posts from authenticated user's feed with filtering statistics"""
    # ... existing code ...
    
    for feed_item in response.feed:
        post = feed_item.post
        
        # ... existing filtering code ...
        
        # Extract self-labels if present
        self_labels = None
        if hasattr(post.record, 'labels') and post.record.labels:
            labels_obj = post.record.labels
            if hasattr(labels_obj, 'values') and labels_obj.values:
                self_labels = [label.val for label in labels_obj.values 
                              if hasattr(label, 'val')]
        
        bluesky_post = BlueskyPost(
            uri=post.uri,
            cid=post.cid,
            text=post.record.text,
            created_at=created_at,
            author_handle=post.author.handle,
            author_display_name=post.author.display_name,
            reply_to=(post.record.reply.parent.uri if post.record.reply else None),
            embed=BlueskyClient._extract_embed_data(post.record.embed) if hasattr(post.record, "embed") and post.record.embed else None,
            facets=BlueskyClient._extract_facets_data(post.record.facets) if hasattr(post.record, "facets") and post.record.facets else None,
            self_labels=self_labels,  # NEW
        )
        posts.append(bluesky_post)
```

3. **Update `MastodonClient.post_status()`** to support content warnings:

```python
def post_status(
    self,
    text: str,
    in_reply_to_id: Optional[str] = None,
    media_ids: Optional[List[str]] = None,
    sensitive: bool = False,  # NEW
    spoiler_text: Optional[str] = None,  # NEW
) -> Optional[Dict[str, Any]]:
    """Post a status to Mastodon"""
    if not self._authenticated or not self.client:
        raise RuntimeError("Client not authenticated. Call authenticate() first.")
    
    try:
        status = self.client.status_post(
            status=text,
            in_reply_to_id=in_reply_to_id,
            media_ids=media_ids,
            sensitive=sensitive,
            spoiler_text=spoiler_text,
        )
        
        logger.info(f"Successfully posted status to Mastodon: {status['id']}")
        return status if isinstance(status, dict) else None
    
    except Exception as e:
        logger.error(f"Failed to post status to Mastodon: {e}")
        return None
```

4. **Add content warning mapping logic** in `src/content_processor.py`:

```python
class ContentProcessor:
    # Mapping of Bluesky self-labels to Mastodon content warnings
    CONTENT_WARNING_LABELS = {
        "porn": "NSFW - Adult Content",
        "sexual": "NSFW - Sexual Content",
        "nudity": "NSFW - Nudity",
        "graphic-media": "Content Warning - Graphic Violence",
    }
    
    @staticmethod
    def get_content_warning_from_labels(self_labels: Optional[List[str]]) -> tuple[bool, Optional[str]]:
        """Convert Bluesky self-labels to Mastodon content warning
        
        Args:
            self_labels: List of Bluesky self-label values
            
        Returns:
            Tuple of (is_sensitive, spoiler_text)
        """
        if not self_labels:
            return (False, None)
        
        # Check if any labels require content warnings
        warnings = []
        for label in self_labels:
            if label in ContentProcessor.CONTENT_WARNING_LABELS:
                warnings.append(ContentProcessor.CONTENT_WARNING_LABELS[label])
        
        if warnings:
            # Mark as sensitive and combine warnings
            spoiler_text = " | ".join(warnings)
            return (True, spoiler_text)
        
        return (False, None)
```

5. **Update `SyncOrchestrator.sync_post()`** to use content warnings:

```python
def sync_post(self, bluesky_post: BlueskyPost) -> bool:
    """Sync a single post from Bluesky to Mastodon"""
    try:
        # ... existing code ...
        
        # Check for content warnings from self-labels
        is_sensitive, spoiler_text = self.content_processor.get_content_warning_from_labels(
            bluesky_post.self_labels
        )
        
        if is_sensitive:
            logger.info(f"Post has content warning: {spoiler_text}")
        
        # Post to Mastodon with content warning if applicable
        mastodon_response = self.mastodon_client.post_status(
            processed_text,
            in_reply_to_id=in_reply_to_id,
            media_ids=media_ids if media_ids else None,
            sensitive=is_sensitive,
            spoiler_text=spoiler_text,
        )
        
        # ... rest of existing code ...
```

6. **Add configuration option** to control content warning behavior:
   - Add `SYNC_CONTENT_WARNINGS` environment variable (default: true)
   - Allow users to opt-out if they want to manually review sensitive content

7. **Add tests**:
   - Test extraction of self-labels from post records
   - Test content warning generation for various label combinations
   - Test that sensitive posts are marked correctly in Mastodon
   - Test configuration option to disable content warnings

---

### 4. Bluesky Post Language Tags

**Category**: Internationalization  
**Severity**: LOW-MEDIUM  
**Current Status**: ❌ NOT HANDLED

**Issue**:
Bluesky posts include a `langs` field (ISO 639-1 language codes) that indicates the post's language(s). Mastodon also supports language tagging, but we don't currently transfer this metadata.

**Impact**:
- Language-based filtering on Mastodon doesn't work for synced posts
- Reduced discoverability for multilingual users
- Accessibility issues for translation features

**AT Protocol Structure**:
```python
# Post record includes:
{
    "text": "...",
    "langs": ["en", "es"],  # ISO 639-1 codes
}
```

**Fix Instructions**:

1. **Update `BlueskyPost` dataclass**:
```python
@dataclass
class BlueskyPost:
    # ... existing fields ...
    langs: Optional[List[str]] = None  # NEW: Language codes
```

2. **Extract language tags in `get_recent_posts()`**:
```python
# In BlueskyClient.get_recent_posts():
bluesky_post = BlueskyPost(
    # ... existing fields ...
    langs=(
        post.record.langs 
        if hasattr(post.record, 'langs') and post.record.langs 
        else None
    ),
)
```

3. **Update `MastodonClient.post_status()`** to support language:
```python
def post_status(
    self,
    text: str,
    in_reply_to_id: Optional[str] = None,
    media_ids: Optional[List[str]] = None,
    sensitive: bool = False,
    spoiler_text: Optional[str] = None,
    language: Optional[str] = None,  # NEW: ISO 639-1 code
) -> Optional[Dict[str, Any]]:
    # ... implementation with language parameter ...
```

4. **Update `SyncOrchestrator.sync_post()`** to pass language:
```python
# Determine primary language (take first if multiple)
language = bluesky_post.langs[0] if bluesky_post.langs else None

mastodon_response = self.mastodon_client.post_status(
    processed_text,
    in_reply_to_id=in_reply_to_id,
    media_ids=media_ids if media_ids else None,
    sensitive=is_sensitive,
    spoiler_text=spoiler_text,
    language=language,
)
```

---

### 5. Media Upload Failure Handling

**Category**: Error Recovery  
**Severity**: MEDIUM-HIGH  
**Current Status**: ⚠️ PARTIALLY HANDLED

**Issue**:
Current implementation in `_sync_images()` logs warnings when image uploads fail but continues posting with partial media. This can result in posts with missing images.

**Current Behavior**:
```python
# In _sync_images():
if media_id:
    media_ids.append(media_id)
else:
    logger.warning(f"Failed to upload image {i+1} to Mastodon for post {bluesky_post.uri}")
# Continues even if some uploads fail
```

**Impact**:
- Posts appear incomplete on Mastodon
- Image captions/alt text may reference missing images
- User confusion about missing content

**Fix Instructions**:

1. **Add configuration option** for failure handling strategy:
```python
# In config.py:
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Image upload failure handling
    # Options: "skip_post", "partial_images", "text_placeholder"
    image_upload_failure_strategy: str = "text_placeholder"
```

2. **Implement failure strategies** in `SyncOrchestrator._sync_images()`:

```python
def _sync_images(self, bluesky_post: BlueskyPost) -> tuple[List[str], bool]:
    """Download images from Bluesky and upload to Mastodon
    
    Returns:
        Tuple of (media_ids list, all_successful boolean)
    """
    media_ids: List[str] = []
    images = self.content_processor.extract_images_from_embed(bluesky_post.embed)
    
    if not images:
        return ([], True)
    
    logger.info(f"Found {len(images)} image(s) to sync for post {bluesky_post.uri}")
    
    failed_count = 0
    
    for i, image_info in enumerate(images):
        try:
            # ... existing image download/upload logic ...
            
            if media_id:
                media_ids.append(media_id)
                logger.info(f"Successfully uploaded image {i+1}/{len(images)}")
            else:
                failed_count += 1
                logger.warning(f"Failed to upload image {i+1}/{len(images)}")
        
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing image {i+1}: {e}")
    
    all_successful = (failed_count == 0)
    
    if failed_count > 0:
        logger.warning(
            f"Image sync partially failed: {failed_count}/{len(images)} uploads failed"
        )
    
    return (media_ids, all_successful)
```

3. **Update `sync_post()` to handle image failures**:

```python
def sync_post(self, bluesky_post: BlueskyPost) -> bool:
    """Sync a single post from Bluesky to Mastodon"""
    try:
        # ... existing code ...
        
        # Handle image attachments
        media_ids = []
        all_images_successful = True
        
        if bluesky_post.embed and not self.settings.dry_run:
            media_ids, all_images_successful = self._sync_images(bluesky_post)
            
            # Apply failure handling strategy
            if not all_images_successful:
                strategy = self.settings.image_upload_failure_strategy
                
                if strategy == "skip_post":
                    logger.warning(
                        f"Skipping post {bluesky_post.uri} due to image upload failure"
                    )
                    return False
                
                elif strategy == "text_placeholder":
                    # Add note about missing images
                    image_count = len(
                        self.content_processor.extract_images_from_embed(bluesky_post.embed)
                    )
                    missing_count = image_count - len(media_ids)
                    
                    note = f"\n\n[Note: {missing_count} image(s) could not be synced]"
                    if len(processed_text + note) <= char_limit:
                        processed_text += note
                
                # "partial_images" strategy: continue with whatever we have
        
        # Post with whatever media we successfully uploaded
        mastodon_response = self.mastodon_client.post_status(
            processed_text,
            in_reply_to_id=in_reply_to_id,
            media_ids=media_ids if media_ids else None,
            sensitive=is_sensitive,
            spoiler_text=spoiler_text,
        )
        
        # ... rest of code ...
```

4. **Add retry logic** for transient failures:
```python
def _upload_image_with_retry(
    self, 
    image_bytes: bytes, 
    mime_type: str, 
    description: str,
    max_retries: int = 3
) -> Optional[str]:
    """Upload image to Mastodon with retry logic"""
    for attempt in range(max_retries):
        try:
            media_id = self.mastodon_client.upload_media(
                media_file=image_bytes,
                mime_type=mime_type,
                description=description,
            )
            if media_id:
                return media_id
        except Exception as e:
            logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    
    return None
```

5. **Add tests**:
   - Test all three failure strategies
   - Test retry logic with transient failures
   - Test mixed success/failure scenarios

---

## Medium Priority Edge Cases

### 6. Bluesky Embed Type: Video

**Category**: Media Handling  
**Severity**: MEDIUM  
**Current Status**: ❌ NOT HANDLED

**Issue**:
Bluesky supports video embeds (`app.bsky.embed.video`), but the current implementation only handles images and external links.

**Impact**:
- Video posts sync as text-only (with placeholder or nothing)
- Loss of rich media content
- Reduced engagement on synced posts

**AT Protocol Structure**:
```python
# Video embed:
{
    "$type": "app.bsky.embed.video",
    "video": {
        "$type": "blob",
        "ref": {"$link": "..."},
        "mimeType": "video/mp4",
        "size": 12345678
    },
    "captions": [...],
    "alt": "Video description"
}
```

**Fix Instructions**:

1. **Update `_extract_embed_data()` in `src/bluesky_client.py`**:
```python
@staticmethod
def _extract_embed_data(embed) -> Optional[Dict[str, Any]]:
    """Extract embed data from AT Protocol embed objects"""
    # ... existing code ...
    
    # === VIDEO EMBEDS ===
    if hasattr(embed, "video") and embed.video:
        video = embed.video
        embed_dict["video"] = {
            "mime_type": getattr(video, "mime_type", "video/mp4"),
            "size": getattr(video, "size", None),
            "alt": getattr(embed, "alt", None),
        }
        
        # Extract blob reference
        if hasattr(video, "ref"):
            ref = video.ref
            if hasattr(ref, "link"):
                embed_dict["video"]["ref"] = {"$link": ref.link}
    
    return embed_dict
```

2. **Add video download method**:
```python
def download_video(self, blob_ref: str, did: str) -> Optional[Tuple[bytes, str]]:
    """Download video blob from AT Protocol
    
    Args:
        blob_ref: The blob reference (CID)
        did: The DID of the post author
        
    Returns:
        Tuple of (video_bytes, mime_type) or None if failed
    """
    # Implementation similar to download_blob() but for video
    # May need to handle larger file sizes and streaming
```

3. **Handle in ContentProcessor**:
```python
@staticmethod
def _handle_embed(text: str, embed: Dict[str, Any], include_image_placeholders: bool = True) -> str:
    # ... existing code ...
    
    elif embed_type == "video":
        video = embed.get("video", {})
        alt_text = video.get("alt", "")
        video_text = f"\n\n🎥 [Video]"
        if alt_text:
            video_text += f"\nDescription: {alt_text}"
        return text + video_text
    
    return text
```

4. **Add Mastodon video upload** (note: may have size/format restrictions):
```python
def upload_video(
    self,
    video_file: bytes,
    mime_type: str,
    description: Optional[str] = None,
) -> Optional[str]:
    """Upload video to Mastodon
    
    Note: Check instance limits for video size/duration
    """
    # Implementation
```

5. **Configuration**:
   - Add `SYNC_VIDEOS` setting (default: false due to size/complexity)
   - Add max video size limit check
   - Consider fallback to link if video too large

---

### 7. Quoted Post Depth and Circular References

**Category**: Content Processing  
**Severity**: MEDIUM  
**Current Status**: ⚠️ PARTIALLY HANDLED

**Issue**:
The current implementation handles simple quoted posts (`app.bsky.embed.record`) but doesn't handle:
- Deeply nested quotes (quote of a quote of a quote...)
- Circular quote references
- Quote + images + external link combinations

**Impact**:
- Complex quote chains may be truncated or malformed
- Potential infinite loops with circular references
- Character limit violations with deep nesting

**Fix Instructions**:

1. **Add quote depth tracking** in `ContentProcessor`:
```python
@staticmethod
def _handle_embed(
    text: str, 
    embed: Dict[str, Any], 
    include_image_placeholders: bool = True,
    quote_depth: int = 0,  # NEW
    max_quote_depth: int = 2,  # NEW
) -> str:
    """Handle embedded content from Bluesky posts
    
    Args:
        quote_depth: Current nesting level of quotes
        max_quote_depth: Maximum allowed quote nesting
    """
    if quote_depth >= max_quote_depth:
        return text + "\n\n[Quoted post - nesting limit reached]"
    
    # ... existing code ...
    
    elif embed_type == "record":
        record = embed.get("record", {})
        if record.get("py_type", "").endswith("ViewRecord"):
            author = record.get("author", {})
            quote_text = record.get("value", {}).get("text", "")
            
            # Check for nested quote
            nested_embed = record.get("embeds", [{}])[0] if record.get("embeds") else None
            
            if author.get("handle") and quote_text:
                quote_preview = quote_text[:100] + "..." if len(quote_text) > 100 else quote_text
                result = text + f"\n\nQuoting @{author['handle']}:\n> {quote_preview}"
                
                # Recursively handle nested embeds with depth tracking
                if nested_embed:
                    result = ContentProcessor._handle_embed(
                        result, 
                        nested_embed,
                        include_image_placeholders,
                        quote_depth=quote_depth + 1,
                        max_quote_depth=max_quote_depth
                    )
                
                return result
```

2. **Add circular reference detection**:
```python
def _handle_embed(
    text: str, 
    embed: Dict[str, Any], 
    include_image_placeholders: bool = True,
    quote_depth: int = 0,
    max_quote_depth: int = 2,
    seen_uris: Optional[set] = None,  # NEW: Track visited URIs
) -> str:
    """Handle embedded content with circular reference detection"""
    if seen_uris is None:
        seen_uris = set()
    
    # ... existing code ...
    
    elif embed_type == "record":
        record = embed.get("record", {})
        record_uri = record.get("uri")
        
        # Check for circular reference
        if record_uri and record_uri in seen_uris:
            return text + "\n\n[Quoted post - circular reference detected]"
        
        if record_uri:
            seen_uris.add(record_uri)
        
        # ... rest of quote handling with seen_uris passed to recursive calls ...
```

3. **Add tests**:
   - Test quote depth limiting
   - Test circular reference detection
   - Test complex embed combinations (quote + images + link)

---

### 8. Bluesky Repost vs Quote Post Distinction

**Category**: Content Classification  
**Severity**: LOW-MEDIUM  
**Current Status**: ⚠️ PARTIALLY HANDLED

**Issue**:
The current implementation filters reposts (pure retweet-style) but doesn't distinguish between:
- Simple reposts (no additional comment) - correctly filtered
- Quote posts with commentary (`app.bsky.embed.record`) - currently synced
- Quote posts with media (`app.bsky.embed.recordWithMedia`) - currently synced

**Current Logic**:
```python
# In get_recent_posts():
if hasattr(feed_item, "reason") and feed_item.reason is not None:
    filtered_reposts += 1
    continue
```

**Impact**:
- Users may want different behavior for reposts vs quotes
- Some users might want to sync quote posts but not simple reposts
- Configuration flexibility needed

**Fix Instructions**:

1. **Add configuration options**:
```python
# In config.py:
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Repost/quote handling
    sync_quote_posts: bool = True  # Quote posts with commentary
    sync_quote_posts_with_media: bool = True  # Quotes with attached media
    add_quote_attribution: bool = True  # Add "Quoting @user:" prefix
```

2. **Enhance embed detection**:
```python
def _is_quote_post(embed: Optional[Dict[str, Any]]) -> bool:
    """Check if post is a quote post"""
    if not embed:
        return False
    
    embed_type = embed.get("py_type", "").split(".")[-1]
    return embed_type in ["record", "recordWithMedia"]

def _is_quote_with_media(embed: Optional[Dict[str, Any]]) -> bool:
    """Check if post is a quote with additional media"""
    if not embed:
        return False
    
    embed_type = embed.get("py_type", "").split(".")[-1]
    return embed_type == "recordWithMedia"
```

3. **Update filtering logic**:
```python
# In get_recent_posts():
for feed_item in response.feed:
    post = feed_item.post
    
    # Filter reposts (existing)
    if hasattr(feed_item, "reason") and feed_item.reason is not None:
        filtered_reposts += 1
        continue
    
    # NEW: Check for quote posts if user wants to filter them
    if hasattr(post.record, "embed") and post.record.embed:
        embed_data = BlueskyClient._extract_embed_data(post.record.embed)
        
        # Filter quote posts based on settings
        if BlueskyClient._is_quote_post(embed_data):
            if not self.settings.sync_quote_posts:
                filtered_quotes += 1  # New counter
                continue
            
            if (BlueskyClient._is_quote_with_media(embed_data) and 
                not self.settings.sync_quote_posts_with_media):
                filtered_quote_media += 1  # New counter
                continue
    
    # ... rest of processing ...
```

4. **Add to BlueskyFetchResult**:
```python
@dataclass
class BlueskyFetchResult:
    posts: List["BlueskyPost"]
    total_retrieved: int
    filtered_replies: int
    filtered_reposts: int
    filtered_by_date: int
    filtered_quote_posts: int = 0  # NEW
    filtered_quote_posts_with_media: int = 0  # NEW
```

---

### 9. Orphaned Media Blobs (Deleted or Inaccessible)

**Category**: Error Handling  
**Severity**: MEDIUM  
**Current Status**: ⚠️ PARTIALLY HANDLED

**Issue**:
Image blob references may become invalid if:
- Original post is deleted
- Media expires or is removed
- Permissions change
- Network/CDN issues

**Current Behavior**:
```python
if not image_data:
    logger.warning(f"Failed to download image {i+1} for post {bluesky_post.uri}")
    continue
# Continues without the image
```

**Impact**:
- Silent failures for deleted media
- No user notification about missing content
- Potential sync state inconsistencies

**Fix Instructions**:

1. **Add detailed error tracking**:
```python
def download_blob(self, blob_ref: str, did: str) -> Optional[Tuple[bytes, str]]:
    """Download image blob from AT Protocol"""
    try:
        # ... existing download logic ...
        
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            logger.error(
                f"Invalid content type for blob {blob_ref}: {content_type}"
            )
            return None
        
        # Check file size (avoid memory issues)
        content_length = int(response.headers.get("content-length", 0))
        max_size = 10 * 1024 * 1024  # 10MB limit
        if content_length > max_size:
            logger.error(
                f"Blob {blob_ref} too large: {content_length} bytes (max: {max_size})"
            )
            return None
        
        return response.content, mime_type
        
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Blob {blob_ref} not found (may be deleted)")
        elif e.response.status_code == 403:
            logger.warning(f"Blob {blob_ref} access forbidden (permissions issue)")
        else:
            logger.error(f"HTTP error downloading blob {blob_ref}: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Failed to download blob {blob_ref}: {e}")
        return None
```

2. **Track media failures in state**:
```python
# In SyncState:
def mark_post_synced(
    self, 
    bluesky_uri: str, 
    mastodon_id: str,
    media_failures: Optional[List[str]] = None  # NEW: Failed media references
):
    """Mark a post as successfully synced with optional media failure tracking"""
    sync_record = {
        "bluesky_uri": bluesky_uri,
        "mastodon_id": mastodon_id,
        "synced_at": datetime.utcnow().isoformat(),
    }
    
    if media_failures:
        sync_record["media_failures"] = media_failures
        logger.info(f"Post synced with {len(media_failures)} media failures")
    
    self.state["synced_posts"].append(sync_record)
    self._save_state()
```

3. **Add media verification before posting**:
```python
def _verify_media_availability(self, bluesky_post: BlueskyPost) -> tuple[bool, List[str]]:
    """Pre-check if media blobs are accessible
    
    Returns:
        Tuple of (all_available, list of unavailable blob refs)
    """
    images = self.content_processor.extract_images_from_embed(bluesky_post.embed)
    unavailable = []
    
    for image_info in images:
        blob_ref = image_info.get("blob_ref")
        if blob_ref:
            # HEAD request to check availability
            try:
                author_did = bluesky_post.uri.split("/")[2]
                blob_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={blob_ref}"
                response = requests.head(blob_url, timeout=5)
                if response.status_code != 200:
                    unavailable.append(blob_ref)
            except Exception:
                unavailable.append(blob_ref)
    
    return (len(unavailable) == 0, unavailable)
```

---

### 10. Mastodon Polls in Replies

**Category**: Feature Completeness  
**Severity**: LOW  
**Current Status**: ❌ NOT HANDLED

**Issue**:
Mastodon supports polls but Bluesky doesn't (yet). If future AT Protocol versions add polls, we need to handle them.

**Impact**:
- Future compatibility issues
- Missing interactive content

**Fix Instructions**:

1. **Add future-proofing check**:
```python
# In _extract_embed_data():
# Log unknown embed types for future investigation
embed_type = embed.get("py_type", "")
known_types = [
    "app.bsky.embed.images",
    "app.bsky.embed.external",
    "app.bsky.embed.record",
    "app.bsky.embed.recordWithMedia",
    "app.bsky.embed.video",
]

if embed_type and not any(embed_type.endswith(t) for t in known_types):
    logger.warning(f"Unknown embed type encountered: {embed_type}")
    # Log for future analysis
```

2. **Prepare for polls**:
```python
# When polls are added to AT Protocol:
elif embed_type == "poll":
    # Convert to text representation for Mastodon
    # Since Mastodon requires polls to be created at post time,
    # we can't recreate the poll, but can show options as text
    pass
```

---

## Low Priority Edge Cases

### 11. Rate Limit Exhaustion and Backoff

**Category**: API Management  
**Severity**: LOW-MEDIUM  
**Current Status**: ⚠️ MINIMAL HANDLING

**Issue**:
Current implementation has basic delays (1 second between posts, 0.5 seconds between images) but no sophisticated rate limit handling.

**API Limits**:
- **Bluesky**: 5000 requests/hour (typically not reached)
- **Mastodon**: 300 requests per 5-minute window, 1000 posts/day

**Fix Instructions**:

1. **Add rate limit tracking**:
```python
class MastodonClient:
    def __init__(self, api_base_url: str, access_token: str):
        # ... existing init ...
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[datetime] = None
    
    def _update_rate_limits(self, response_headers: Dict[str, str]):
        """Update rate limit info from response headers"""
        if "X-RateLimit-Remaining" in response_headers:
            self._rate_limit_remaining = int(response_headers["X-RateLimit-Remaining"])
        
        if "X-RateLimit-Reset" in response_headers:
            reset_timestamp = int(response_headers["X-RateLimit-Reset"])
            self._rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
    
    def _should_wait_for_rate_limit(self) -> bool:
        """Check if we should wait before making next request"""
        if self._rate_limit_remaining is not None:
            # Conservative threshold: wait if < 10 requests remaining
            if self._rate_limit_remaining < 10:
                logger.warning(
                    f"Approaching rate limit: {self._rate_limit_remaining} requests remaining"
                )
                return True
        return False
```

2. **Implement exponential backoff**:
```python
def _wait_for_rate_limit_reset(self):
    """Wait until rate limit resets"""
    if self._rate_limit_reset:
        now = datetime.utcnow()
        if self._rate_limit_reset > now:
            wait_seconds = (self._rate_limit_reset - now).total_seconds()
            logger.info(f"Rate limit reached, waiting {wait_seconds:.0f}s")
            time.sleep(min(wait_seconds, 300))  # Max 5 min wait
```

3. **Add to orchestrator**:
```python
def run_sync(self) -> dict:
    """Run the main sync process"""
    # ... existing code ...
    
    for post in posts_to_sync:
        # Check rate limits before syncing
        if self.mastodon_client._should_wait_for_rate_limit():
            self.mastodon_client._wait_for_rate_limit_reset()
        
        if self.sync_post(post):
            synced_count += 1
            # Adaptive delay based on remaining rate limit
            delay = self._calculate_adaptive_delay()
            if synced_count < len(posts_to_sync):
                time.sleep(delay)
```

---

### 12. Mastodon Idempotency Keys

**Category**: Reliability  
**Severity**: LOW  
**Current Status**: ❌ NOT HANDLED

**Issue**:
Mastodon supports `Idempotency-Key` headers to prevent duplicate posts if a request is retried. We don't currently use this.

**Impact**:
- Network failures may cause duplicate posts
- Retry logic could create duplicates

**Fix Instructions**:

1. **Add idempotency key generation**:
```python
import hashlib

def _generate_idempotency_key(self, bluesky_uri: str, text: str) -> str:
    """Generate deterministic idempotency key for a post"""
    # Combine URI and first 100 chars of text for uniqueness
    content = f"{bluesky_uri}:{text[:100]}"
    return hashlib.sha256(content.encode()).hexdigest()
```

2. **Use in post_status**:
```python
def post_status(
    self,
    text: str,
    in_reply_to_id: Optional[str] = None,
    media_ids: Optional[List[str]] = None,
    idempotency_key: Optional[str] = None,  # NEW
) -> Optional[Dict[str, Any]]:
    """Post a status to Mastodon"""
    if not self._authenticated or not self.client:
        raise RuntimeError("Client not authenticated. Call authenticate() first.")
    
    try:
        # Mastodon.py doesn't directly support idempotency keys
        # Need to use _Mastodon__api_request with custom headers
        if idempotency_key:
            # Use internal API with custom headers
            # (requires extending Mastodon.py or using requests directly)
            pass
        
        status = self.client.status_post(
            status=text,
            in_reply_to_id=in_reply_to_id,
            media_ids=media_ids,
        )
        # ... rest of implementation ...
```

---

### 13. Bluesky Facet Edge Cases

**Category**: Content Processing  
**Severity**: LOW-MEDIUM  
**Current Status**: ⚠️ BASIC HANDLING

**Issue**:
Facets can have edge cases:
- Overlapping facet ranges
- Invalid byte positions (past end of text)
- Facets with no features
- Malformed facet data

**Fix Instructions**:

1. **Add facet validation**:
```python
@staticmethod
def _validate_facet(facet: Dict[str, Any], text_length: int) -> bool:
    """Validate facet has valid byte positions and features"""
    try:
        index = facet.get("index", {})
        byte_start = index.get("byteStart")
        byte_end = index.get("byteEnd")
        
        if byte_start is None or byte_end is None:
            return False
        
        if byte_start < 0 or byte_end < 0:
            return False
        
        if byte_start >= byte_end:
            return False
        
        if byte_end > text_length:
            return False
        
        features = facet.get("features", [])
        if not features:
            return False
        
        return True
    except Exception:
        return False
```

2. **Filter invalid facets**:
```python
@staticmethod
def _expand_urls_from_facets(text: str, facets: List[Dict[str, Any]]) -> str:
    """Expand truncated URLs using facets data from Bluesky"""
    if not facets:
        return text
    
    text_bytes = text.encode('utf-8')
    text_length = len(text_bytes)
    
    # Filter out invalid facets
    valid_facets = [
        f for f in facets 
        if ContentProcessor._validate_facet(f, text_length)
    ]
    
    if len(valid_facets) < len(facets):
        logger.warning(
            f"Filtered out {len(facets) - len(valid_facets)} invalid facets"
        )
    
    # ... rest of processing with valid_facets ...
```

---

### 14. Thread Depth Limits on Mastodon

**Category**: Platform Limitation  
**Severity**: LOW  
**Current Status**: ❌ NOT DOCUMENTED

**Issue**:
Mastodon instances may have limits on thread depth (typically ~100 levels), but we don't check or warn about this.

**Impact**:
- Very deep Bluesky threads may not sync completely
- Silent truncation of thread chains

**Fix Instructions**:

1. **Add thread depth tracking**:
```python
def _get_thread_depth(self, mastodon_id: str) -> int:
    """Calculate depth of a post in its thread
    
    Returns 0 for root posts, 1 for first-level replies, etc.
    """
    depth = 0
    current_id = mastodon_id
    
    # Traverse up the thread
    while current_id and depth < 100:  # Safety limit
        # Look up parent in sync state
        parent_id = self.sync_state.get_parent_id(current_id)
        if not parent_id:
            break
        current_id = parent_id
        depth += 1
    
    return depth
```

2. **Check before posting**:
```python
def sync_post(self, bluesky_post: BlueskyPost) -> bool:
    """Sync a single post from Bluesky to Mastodon"""
    # ... existing code ...
    
    if in_reply_to_id:
        thread_depth = self._get_thread_depth(in_reply_to_id)
        if thread_depth >= 90:  # Conservative limit
            logger.warning(
                f"Thread depth ({thread_depth}) approaching Mastodon limits, "
                f"posting as standalone instead"
            )
            in_reply_to_id = None
    
    # ... rest of code ...
```

---

### 15. Character Counting Edge Cases

**Category**: Content Processing  
**Severity**: LOW  
**Current Status**: ⚠️ SIMPLE IMPLEMENTATION

**Issue**:
Current character counting uses Python's `len()` which counts Unicode characters. Mastodon's character counting may differ for:
- Emoji (some count as 1, some as 2 or more)
- URLs (shortened to fixed length like 23 characters)
- Invisible characters
- Zero-width joiners (ZWJ) in complex emoji

**Fix Instructions**:

1. **Use Mastodon's character counting**:
```python
def _count_mastodon_characters(self, text: str, has_media: bool = False) -> int:
    """Count characters using Mastodon's counting rules
    
    Rules:
    - URLs count as 23 characters regardless of actual length
    - Emoji may count differently than Python len()
    - Domain names in links may be excluded from count
    """
    # Extract URLs
    urls = ContentProcessor.extract_urls(text)
    
    char_count = len(text)
    
    # Subtract actual URL length, add fixed count
    for url in urls:
        char_count -= len(url)
        char_count += 23  # Mastodon's URL character count
    
    return char_count
```

2. **Use in truncation logic**:
```python
@staticmethod
def _truncate_if_needed(text: str, char_limit: int = 500) -> str:
    """Truncate text if it exceeds character limit using Mastodon's counting"""
    actual_count = ContentProcessor._count_mastodon_characters(text)
    
    if actual_count <= char_limit:
        return text
    
    # ... rest of truncation logic using actual_count ...
```

---

## Testing Recommendations

### Integration Tests Needed

1. **Multi-byte Character Integration Test**:
   - Test full pipeline with emoji-heavy posts
   - Verify URL expansion with international characters
   - Test CJK character handling

2. **Content Warning Integration Test**:
   - Test self-labeled posts end-to-end
   - Verify Mastodon CW display
   - Test combinations of labels

3. **Media Failure Scenarios**:
   - Test partial image upload failures
   - Test deleted blob handling
   - Test retry logic under various failure modes

4. **Rate Limit Simulation**:
   - Mock rate limit headers from Mastodon
   - Test backoff behavior
   - Verify sync completion after rate limit reset

5. **Deep Thread Test**:
   - Create Bluesky thread with 20+ levels
   - Verify all posts sync in correct order
   - Check thread structure on Mastodon

### Load Testing

1. **Bulk Sync Test**:
   - Sync 100+ posts in one run
   - Monitor memory usage
   - Check state file size growth

2. **Large Media Test**:
   - Test with maximum allowed images (4 per post)
   - Test with large image files (close to Mastodon limits)
   - Verify upload timeouts are appropriate

3. **Character Limit Stress Test**:
   - Test posts near 500-character limit
   - Test with maximum embeds (link + 4 images + quote)
   - Verify truncation doesn't break formatting

---

## Implementation Priority

### Phase 1 (Critical - Implement First):
1. Multi-byte character handling in facet expansion
2. Mastodon instance character limit detection
3. Content warning/self-label support
4. Media upload failure handling improvements

### Phase 2 (Important - Implement Soon):
5. Language tag support
6. Video embed handling
7. Quote post depth limiting
8. Orphaned media blob handling

### Phase 3 (Enhancement - Nice to Have):
9. Repost vs quote post configuration
10. Rate limit tracking and backoff
11. Mastodon idempotency keys
12. Thread depth warnings

### Phase 4 (Future-Proofing):
13. Facet validation improvements
14. Character counting refinements
15. Unknown embed type logging

---

## Monitoring and Alerting

### Recommended Metrics to Track

1. **Failure Rates**:
   - Image download failures per sync run
   - Image upload failures per sync run
   - Post sync failures with error categories

2. **Content Warnings**:
   - Number of posts with self-labels synced
   - Content warning types encountered

3. **Character Limit**:
   - Posts truncated count
   - Average character count before/after processing

4. **Threading**:
   - Thread depth distribution
   - Orphaned replies count

### Logging Enhancements

```python
# Add structured logging
import logging
import json

class StructuredLogger:
    @staticmethod
    def log_sync_metrics(metrics: dict):
        logger.info(f"SYNC_METRICS: {json.dumps(metrics)}")
    
    @staticmethod
    def log_failure(category: str, details: dict):
        logger.warning(f"SYNC_FAILURE: {category} - {json.dumps(details)}")
```

---

## Conclusion

This analysis identified **15 distinct edge cases** across the Bluesky AT Protocol and Mastodon API integration:

- **5 Critical/High Priority**: Multi-byte characters, instance limits, content warnings, media failures, language tags
- **5 Medium Priority**: Video support, quote depth, orphaned media, polls, repost configuration  
- **5 Low Priority**: Rate limits, idempotency, facet validation, thread depth, character counting

Each edge case includes:
- ✅ Severity assessment
- ✅ Current implementation status
- ✅ Impact analysis
- ✅ Detailed fix instructions with code examples
- ✅ Testing recommendations

The recommended implementation follows a phased approach, prioritizing issues that could cause:
1. Data corruption or loss (multi-byte characters)
2. Content policy violations (missing content warnings)
3. User experience degradation (truncated content, missing media)
4. Future compatibility issues (unknown embed types)

All fixes are designed to maintain backward compatibility with the existing codebase and sync state format.
