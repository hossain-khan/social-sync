# API Documentation for Social Sync

This document provides technical details about the Social Sync implementation, APIs used, and architecture.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub        │    │   Social Sync   │    │   Mastodon      │
│   Actions       │───▶│   Orchestrator  │───▶│   API           │
│   (Scheduler)   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Bluesky       │
                       │   AT Protocol   │
                       │   API           │
                       └─────────────────┘
```

## Core Components

### 1. Configuration Management (`config.py`)

**Purpose**: Centralized configuration using Pydantic settings

**Key Features**:
- Environment variable loading
- Validation of required credentials
- Type-safe configuration access

**Environment Variables**:
```python
BLUESKY_HANDLE: str          # User's Bluesky handle
BLUESKY_PASSWORD: str        # Bluesky app password
MASTODON_API_BASE_URL: str   # Mastodon instance URL
MASTODON_ACCESS_TOKEN: str   # Mastodon API token
SYNC_INTERVAL_MINUTES: int   # Sync frequency (default: 60)
MAX_POSTS_PER_SYNC: int     # Max posts per run (default: 10)
DRY_RUN: bool               # Test mode flag (default: false)
LOG_LEVEL: str              # Logging level (default: INFO)
```

### 2. Bluesky Client (`bluesky_client.py`)

**Purpose**: Wrapper around the AT Protocol Python SDK

**Key Methods**:
- `authenticate()`: Login with handle/password
- `get_recent_posts(limit, since_date)`: Fetch user's recent posts with optional date filtering
- `get_post_thread(uri)`: Get post context/thread information
- `get_user_did()`: Get user's decentralized identifier (DID)
- `download_blob(blob_ref, did)`: Download images and media from AT Protocol

**Post Data Structure**:
```python
@dataclass
class BlueskyPost:
    uri: str                    # AT Protocol URI
    cid: str                    # Content identifier
    text: str                   # Post text content
    created_at: datetime        # Post timestamp
    author_handle: str          # Author's handle
    author_display_name: str    # Author's display name
    reply_to: Optional[str]     # Reply parent URI (for threading)
    embed: Optional[Dict]       # Embedded content (links, images, quotes)
    facets: List[Dict]          # Facets for hashtags, mentions, links
```

**Threading Support**:
- The `reply_to` field contains the AT Protocol URI of the parent post
- Thread structure is detected automatically during sync processing
- Parent-child relationships are preserved across platform boundaries

### 3. Mastodon Client (`mastodon_client.py`)

**Purpose**: Wrapper around the Mastodon.py library

**Key Methods**:
- `authenticate()`: Verify API credentials
- `post_status(text, reply_to, media)`: Create new status with optional threading
- `upload_media(file, description)`: Upload media files
- `get_recent_posts(limit)`: Fetch user's posts

**Threading Support**:
- The `in_reply_to_id` parameter maintains conversation threads
- Supports nested replies up to Mastodon's depth limits
- Thread context is preserved when syncing from Bluesky conversations

**API Endpoints Used**:
- `POST /api/v1/statuses` - Create status
- `POST /api/v1/media` - Upload media
- `GET /api/v1/accounts/verify_credentials` - Verify auth
- `GET /api/v1/accounts/{id}/statuses` - Get user posts

### 4. Content Processor (`content_processor.py`)

**Purpose**: Adapt content between platform formats

**Processing Steps**:
1. **Embed Handling**: Convert AT Protocol embeds to text or media
2. **Image Processing**: Download and upload images with alt text
3. **Mention Conversion**: Handle @mentions format differences  
4. **Character Limit**: Truncate to Mastodon's 500 char limit
5. **Attribution**: Add "(via Bluesky)" tag

**Embed Types Supported**:
- **External Links**: Convert to text with URL
- **Images**: Download from Bluesky and upload to Mastodon with alt text
- **Quoted Posts**: Include quote preview with attribution
- **Record Embeds**: Handle referenced content

**Image Syncing Features**:
- Downloads images via AT Protocol blob API
- Uploads to Mastodon with proper MIME types
- Preserves alt text descriptions
- Supports multiple images per post
- Graceful fallback to text placeholders if image sync fails

### 5. State Management (`sync_state.py`)

**Purpose**: Track sync history and prevent duplicates

**State File Structure** (`sync_state.json`):
```json
{
  "last_sync_time": "2024-01-15T10:30:00",
  "synced_posts": [
    {
      "bluesky_uri": "at://did:plc:abc123/app.bsky.feed.post/xyz789",
      "mastodon_id": "12345678",
      "synced_at": "2024-01-15T10:30:00"
    }
  ],
  "last_bluesky_post_uri": "at://did:plc:abc123/app.bsky.feed.post/xyz789"
}
```

**Key Methods**:
- `is_post_synced(uri)`: Check if post already processed
- `mark_post_synced(uri, mastodon_id)`: Record successful sync
- `cleanup_old_records(days)`: **DEPRECATED** - No longer removes old records. All sync state records are now preserved indefinitely. Method kept for backward compatibility only.

### 6. Sync Orchestrator (`sync_orchestrator.py`)

**Purpose**: Coordinate the entire sync process

**Sync Flow**:
1. Initialize and authenticate clients
2. Fetch recent posts from Bluesky
3. Filter out already-synced posts
4. Process each new post:
   - **Thread Detection**: Check for `reply_to` field in Bluesky post
   - **Parent Lookup**: Find corresponding Mastodon post ID for threaded replies
   - Transform content for Mastodon
   - Post to Mastodon with thread information (if not dry-run)
   - Update sync state with post mappings
5. Clean up old state records
6. Return sync results

**Threading Logic**:
- Detects reply posts via AT Protocol `reply_to` field
- Looks up parent post's Mastodon ID from sync state
- Posts replies using Mastodon's `in_reply_to_id` parameter
- Maintains conversation context across platforms
- Gracefully handles orphaned replies (parent not synced)

## API Integration Details

### Bluesky AT Protocol

**Authentication**:
```python
# Using atproto library
client = Client()
session = client.login(handle, password)
```

**Fetching Posts**:
```python
# Get author feed
response = client.get_author_feed(
    actor=handle,
    limit=limit
)
```

**Rate Limits**:
- 5000 requests per hour per authenticated user
- Additional blob download limits may apply for image syncing
- No specific posting limits documented

### Mastodon API

**Authentication**:
```python
# Using Mastodon.py library
client = Mastodon(
    access_token=token,
    api_base_url=instance_url
)
```

**Creating Posts**:
```python
# Post status
status = client.status_post(
    status=text,
    in_reply_to_id=reply_id,
    media_ids=media_list
)
```

**Rate Limits**:
- 300 requests per 5-minute window
- 1000 posts per day per account

## Error Handling

### Common Error Scenarios

**Authentication Errors**:
- Invalid credentials
- Expired tokens
- Network connectivity issues

**API Rate Limiting**:
- Bluesky: Exponential backoff recommended
- Mastodon: Built-in rate limit handling

**Content Processing Errors**:
- Malformed embed data
- Encoding issues
- Character limit violations

### Error Recovery Strategies

1. **Retry Logic**: Exponential backoff for transient errors
2. **Graceful Degradation**: Skip problematic posts, continue with others
3. **State Preservation**: Don't mark posts as synced if posting fails
4. **Detailed Logging**: Log all errors with context for debugging

## Performance Considerations

### Optimization Strategies

**Batch Processing**: Process multiple posts efficiently
**Caching**: Cache client sessions and API responses where appropriate
**State Management**: Efficient duplicate detection using URI tracking
**Resource Usage**: Minimal memory footprint for GitHub Actions

### Scalability Limits

**GitHub Actions**: 6-hour maximum runtime, 2GB memory limit
**API Rate Limits**: Mastodon 300/5min, Bluesky 5000/hour
**State File Size**: Limited to ~100 recent posts to prevent growth

## Security Model

### Credential Management

**Secrets Storage**: GitHub Secrets for production credentials
**Local Development**: `.env` files (gitignored)
**Access Tokens**: Minimal required scopes (`write:statuses` for Mastodon)

### Data Privacy

**No Data Storage**: Posts are processed in memory only
**State Information**: Only URIs and timestamps stored locally
**Network Security**: HTTPS for all API communications

## Monitoring and Logging

### Log Levels

- **DEBUG**: Detailed API calls and processing steps
- **INFO**: Sync progress and results
- **WARNING**: Non-fatal issues and recoverable errors
- **ERROR**: Failed operations and authentication issues

### Metrics Tracked

- Posts synced per run
- Sync duration
- Error counts by type
- API response times (when available)

### GitHub Actions Integration

**Artifacts**: Log files uploaded for debugging
**Status Reporting**: Success/failure status in workflow
**Manual Triggers**: Support for manual sync runs

## Extending the System

### Adding New Platforms

To add support for additional platforms:

1. Create client wrapper (following existing patterns)
2. Implement content processor adaptations
3. Update orchestrator with new client
4. Add configuration options
5. Update documentation

### Custom Content Processing

Content processing is modular and can be extended:

- Custom embed handlers
- Platform-specific formatting
- Advanced mention/hashtag processing
- Media handling improvements

### Advanced Features

Potential enhancements:
- Bi-directional sync
- Custom post filtering
- Media upload support
- Thread/reply chain handling
- Real-time sync via webhooks
