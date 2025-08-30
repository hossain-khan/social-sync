# Setup Guide 🛠️

Complete installation and configuration guide for Social Sync.

## Prerequisites

- **Bluesky account** with app password capability
- **Mastodon account** with API access  
- **GitHub account** (for automated syncing)
- **Python 3.11+** for local development

## 1. Get Your Credentials

### Bluesky Credentials
1. Go to **Bluesky Settings** → **App Passwords**
2. Click **Create App Password**
3. Note your handle (e.g., `yourusername.bsky.social`) and the generated password

### Mastodon Credentials
1. Go to your **Mastodon instance** → **Preferences** → **Development**
2. Click **New application**
3. **Application name**: `Social Sync` (or any name)
4. **Scopes**: Ensure `write:statuses` is selected
5. **Submit** and note your instance URL and **Access Token**

## 2. Local Development Setup

```bash
# Clone repository
git clone https://github.com/your-username/social-sync.git
cd social-sync

# Create Python virtual environment  
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### Configure Environment Variables

Edit `.env` file with your credentials:

```bash
# Bluesky Credentials
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password

# Mastodon Credentials
MASTODON_API_BASE_URL=https://your-instance.social
MASTODON_ACCESS_TOKEN=your-access-token

# Sync Configuration
SYNC_INTERVAL_MINUTES=60
MAX_POSTS_PER_SYNC=10
SYNC_START_DATE=7d  # or specific date: 2025-01-01
DRY_RUN=false
LOG_LEVEL=INFO
```

### Test Your Setup

```bash
# Test API connections
python sync.py test

# Run a dry sync to verify functionality
python sync.py sync --dry-run

# Check current configuration
python sync.py config
```

## 3. GitHub Actions Automation

### Step 1: Fork Repository

1. **Fork** this repository to your GitHub account
2. **Clone** your fork locally

### Step 2: Create Personal Access Token

1. Go to **GitHub Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
2. Click **Generate new token**
3. **Repository access**: Select your `social-sync` repository
4. **Permissions**:
   - **Contents**: Read and write ✅
   - **Metadata**: Read ✅
   - **Pull requests**: Write (optional) ✅
5. **Generate token** and copy it immediately

### Step 3: Configure Repository Secrets

Go to your repository **Settings** → **Secrets and variables** → **Actions**:

| Secret Name | Value | Purpose |
|-------------|--------|---------|
| `PAT_TOKEN` | Your Personal Access Token | Branch protection bypass |
| `BLUESKY_HANDLE` | Your Bluesky handle | Authentication |
| `BLUESKY_PASSWORD` | Your app password | Authentication |
| `MASTODON_API_BASE_URL` | Your instance URL | API connection |
| `MASTODON_ACCESS_TOKEN` | Your access token | API authorization |

### Step 4: Test Automation

1. Go to **Actions** → **Social Sync** → **Run workflow**
2. Enable **dry_run** for initial test
3. Click **Run workflow** and check logs
4. If successful, run without dry-run mode

## Branch Protection & CI Setup

### The Problem

When branch protection rules are enabled on `main`, GitHub Actions cannot push sync state updates by default, causing workflow failures:

- ✅ Posts sync successfully
- ❌ Sync state isn't saved
- ⚠️ **Next run re-syncs same posts** (potential duplicates)

### Solution: Personal Access Token (Recommended)

The PAT approach provides reliable branch protection bypass:

1. **Create PAT**: Follow Step 2 above
2. **Add Secret**: Add `PAT_TOKEN` repository secret  
3. **Automatic Bypass**: Workflow uses PAT for elevated permissions

**Why this works:** PATs have higher privileges than default `GITHUB_TOKEN` and can bypass protection rules.

### Alternative: GitHub Actions Bypass

If you prefer rulesets configuration:

1. Go to **Repository Settings** → **Rules** → **Rulesets**
2. **Edit** your main branch ruleset
3. **Bypass list** → **Add bypass** → **GitHub App**
4. Add `github-actions` to bypass list
5. **Save ruleset**

**Note:** This approach may not work with all ruleset configurations.

### Verification

After setup:
1. **Manual trigger**: Actions → Social Sync → Run workflow  
2. **Check commits**: Verify sync state commits appear in git history
3. **Monitor logs**: Ensure no "Failed to push" errors

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BLUESKY_HANDLE` | - | Your Bluesky handle (required) |
| `BLUESKY_PASSWORD` | - | App password (required) |
| `MASTODON_API_BASE_URL` | - | Instance URL (required) |
| `MASTODON_ACCESS_TOKEN` | - | Access token (required) |
| `SYNC_INTERVAL_MINUTES` | 60 | GitHub Actions cron frequency |
| `MAX_POSTS_PER_SYNC` | 10 | Posts processed per sync |
| `SYNC_START_DATE` | 7d | Initial sync date |
| `DRY_RUN` | false | Test mode without posting |
| `LOG_LEVEL` | INFO | Logging verbosity |

### Sync Start Date Examples

```bash
# Relative dates
SYNC_START_DATE=7d        # 7 days ago
SYNC_START_DATE=1w        # 1 week ago
SYNC_START_DATE=30d       # 30 days ago

# Specific dates (beginning of day UTC)
SYNC_START_DATE=2025-01-01
SYNC_START_DATE=2025-01-15

# Specific datetime (UTC if no timezone)
SYNC_START_DATE=2025-01-15T10:30:00

# With timezone
SYNC_START_DATE=2025-01-15T10:30:00-05:00

# CLI override
python sync.py sync --since-date 2025-01-01
```

## State Persistence in CI

### How It Works

1. **Before sync**: Workflow downloads existing `sync_state.json` from repository
2. **During sync**: Application updates sync state with new posts
3. **After sync**: Workflow commits updated state back to main branch
4. **Backup**: State also uploaded as workflow artifact

### File Structure

```json
{
  "last_sync_time": "2025-08-30T16:38:47.586815",
  "synced_posts": [
    {
      "bluesky_uri": "at://did:plc:example/app.bsky.feed.post/abc123",
      "mastodon_id": "123456789",  
      "synced_at": "2025-08-30T16:38:47.586815"
    }
  ],
  "last_bluesky_post_uri": "at://did:plc:example/app.bsky.feed.post/xyz789"
}
```

### Benefits

- **Prevents duplicates** across workflow runs
- **Enables threading** by tracking parent posts
- **Provides audit trail** of all synced content
- **Supports recovery** via artifact backups

## Content Processing

### What Gets Synced

- ✅ **Text posts** - Plain text content
- ✅ **Posts with links** - External URLs with preview
- ✅ **Posts with images** - Images with alt text
- ✅ **Quoted posts** - Includes quoted content
- ✅ **Threaded posts** - Reply posts with conversation context

### What Doesn't Get Synced

- ❌ **Other user replies** - Unless parent was also synced
- ❌ **Reposts/boosts** - Only original content
- ❌ **Already synced** - Prevented by state tracking

### Content Adaptations

- **Threading**: Reply posts become Mastodon replies to maintain conversation
- **Character limits**: Long posts truncated to 500 characters
- **Link embedding**: Bluesky link cards converted to text with URLs  
- **Image handling**: Notes image count and preserves alt text
- **Quote posts**: Includes quoted content with attribution
- **Attribution**: Adds "(via Bluesky)" to posts (skipped for replies)

## Troubleshooting

### Authentication Issues

**Error**: "Authentication failed"
- ✅ Verify Bluesky handle format: `username.bsky.social`
- ✅ Check app password (not account password)
- ✅ Confirm Mastodon instance URL format: `https://instance.social`
- ✅ Validate access token has `write:statuses` scope

### GitHub Actions Failures

**Error**: "Failed to push to protected main branch"
- **Cause**: Branch protection blocking commits
- **Solution**: Add PAT_TOKEN secret with elevated permissions
- **Verification**: Check Actions logs for successful push

**Error**: "Repository rule violations found"
- **Cause**: Repository rulesets requiring PR workflow
- **Solution**: Use PAT_TOKEN for bypass capability
- **Alternative**: Configure Actions bypass in rulesets

### Sync Issues

**Posts not syncing**:
- Check if posts are replies to others (filtered by default)
- Verify posts aren't already in sync state  
- Review logs with `LOG_LEVEL=DEBUG`

**Duplicate posts after CI failure**:
- **Cause**: Sync completed but state not saved
- **Fix**: Resolve branch protection issue
- **Recovery**: Manually update sync state if needed

**Character limit issues**:
- Long posts automatically truncated
- Check processed content in logs
- Consider breaking long posts into threads

### Debug Commands

```bash
# Enable debug logging
LOG_LEVEL=DEBUG python sync.py sync --dry-run

# Check current sync state
python sync.py status

# Validate API connections
python sync.py test  

# View processed configuration
python sync.py config

# Test specific date range
python sync.py sync --since-date 2025-01-01 --dry-run
```

### Common Log Messages

| Message | Meaning | Action |
|---------|---------|---------|
| "Authentication successful" | API credentials valid | ✅ Continue |
| "X posts filtered out" | Posts skipped (replies/reposts) | ✅ Expected |
| "Already synced" | Duplicate prevention working | ✅ Expected |
| "Thread parent not found" | Reply without synced parent | ⚠️ Posted standalone |
| "Failed to push" | Branch protection issue | ❌ Fix PAT setup |

## Security Best Practices

### Credential Management

- ✅ **Never commit** credentials to repository
- ✅ **Use GitHub Secrets** for sensitive data  
- ✅ **App passwords** preferred over main passwords
- ✅ **Rotate tokens** regularly
- ✅ **Minimum scope** - only required permissions

### Repository Security

- ✅ **Branch protection** enabled on main
- ✅ **Required status checks** for PR validation
- ✅ **PAT with limited scope** for automation
- ✅ **Secret scanning** enabled
- ✅ **Dependency updates** via Dependabot

### Access Control

- ✅ **Fine-grained PATs** over classic tokens
- ✅ **Repository-specific** access only
- ✅ **Time-limited** token expiration
- ✅ **Audit logs** review periodically

---

**Need additional help?** Check the [Issues](../../issues) page or create a detailed bug report.
