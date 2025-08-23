# Social Sync 🔄

A Python-based tool to automatically sync posts from Bluesky to Mastodon, designed to run as a GitHub Actions cron job.

## Features ✨

- 🔄 **Automated Syncing**: Sync posts from Bluesky to Mastodon on a schedule
- 🚀 **GitHub Actions Integration**: Runs automatically using GitHub Actions
- 🎯 **Smart Deduplication**: Tracks synced posts to avoid duplicates
- 📝 **Content Processing**: Handles embedded links, images, and quoted posts
- 🔒 **Secure Configuration**: Uses GitHub Secrets for credentials
- 🧪 **Dry Run Mode**: Test without actually posting
- 📊 **Comprehensive Logging**: Detailed logs and status reporting

## Setup Guide 🛠️

### 1. Prerequisites

- A Bluesky account with an app password
- A Mastodon account with API access
- A GitHub account (for automated syncing)

### 2. Get Your Credentials

#### Bluesky Credentials
1. Go to Bluesky Settings → App Passwords
2. Create a new app password
3. Note your handle (e.g., `yourusername.bsky.social`) and the app password

#### Mastodon Credentials
1. Go to your Mastodon instance → Preferences → Development
2. Create a new application with `write:statuses` scope
3. Note your instance URL and access token

### 3. Local Setup

```bash
# Clone the repository
git clone https://github.com/your-username/social-sync.git
cd social-sync

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

### 4. Configure Environment Variables

Edit `.env` file:

```bash
# Bluesky Credentials
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password

# Mastodon Credentials
MASTODON_API_BASE_URL=https://your-instance.social
MASTODON_ACCESS_TOKEN=your-access-token

# Sync Configuration
SYNC_INTERVAL_MINUTES=15
MAX_POSTS_PER_SYNC=10
DRY_RUN=false
LOG_LEVEL=INFO
```

### 5. GitHub Actions Setup

1. Fork this repository
2. Go to Settings → Secrets and variables → Actions
3. Add the following secrets:
   - `BLUESKY_HANDLE`: Your Bluesky handle
   - `BLUESKY_PASSWORD`: Your Bluesky app password
   - `MASTODON_API_BASE_URL`: Your Mastodon instance URL
   - `MASTODON_ACCESS_TOKEN`: Your Mastodon access token

## Usage 📖

### Command Line Interface

```bash
# Run a sync (locally)
python sync.py sync

# Run in dry-run mode (test without posting)
python sync.py sync --dry-run

# Check sync status
python sync.py status

# View configuration
python sync.py config

# Test connections
python sync.py test
```

### GitHub Actions

The sync runs automatically every 15 minutes via GitHub Actions. You can also:

- **Manual trigger**: Go to Actions → Social Sync → Run workflow
- **Dry run**: Use the manual trigger with dry-run mode enabled
- **View logs**: Check the Actions tab for execution logs

### 🔄 State Persistence in CI

**Problem**: GitHub Actions runs in fresh environments, which would normally cause duplicate posts every run.

**Solution**: The workflow uses GitHub Actions Cache to persist the `sync_state.json` file between runs:

1. **Before sync**: Restores previous sync state from cache
2. **After sync**: Saves updated sync state to cache for next run
3. **Backup**: Also uploads state as artifact for recovery

This ensures duplicate posts are prevented even in automated CI runs! 🎯

## How It Works 🔧

1. **Authentication**: Connects to both Bluesky and Mastodon APIs
2. **Fetch Posts**: Gets recent posts from your Bluesky feed
3. **Content Processing**: Adapts content for Mastodon (handles links, images, character limits)
4. **Deduplication**: Checks against previous syncs to avoid duplicates
5. **Post Creation**: Creates corresponding posts on Mastodon
6. **State Tracking**: Updates sync state for future runs

## Content Processing 📝

### What Gets Synced
- ✅ Text posts
- ✅ Posts with external links (with preview)
- ✅ Posts with images (with alt text)
- ✅ Quoted posts (with quote preview)

### What Doesn't Get Synced
- ❌ Replies to other users
- ❌ Reposts/boosts
- ❌ Posts already synced

### Content Adaptations
- **Character Limit**: Truncates posts that exceed Mastodon's 500-character limit
- **Link Embeds**: Converts Bluesky link cards to text with URLs
- **Image Handling**: Notes image count and includes alt text
- **Quote Posts**: Includes quoted content with attribution
- **Attribution**: Adds "(via Bluesky)" to synced posts

## Configuration Options ⚙️

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Sync Interval | `SYNC_INTERVAL_MINUTES` | 15 | How often to sync (GitHub Actions cron) |
| Max Posts | `MAX_POSTS_PER_SYNC` | 10 | Maximum posts to process per sync |
| **Sync Start Date** | `SYNC_START_DATE` | 7 days ago | Start date for syncing posts (ISO format) |
| Dry Run | `DRY_RUN` | false | Test mode without actual posting |
| Log Level | `LOG_LEVEL` | INFO | Logging verbosity |

### 📅 Sync Start Date Examples

```bash
# Start from a specific date (beginning of day UTC)
SYNC_START_DATE=2025-01-01

# Start from a specific datetime (assumes UTC if no timezone)
SYNC_START_DATE=2025-01-15T10:30:00

# Start from a specific datetime with timezone
SYNC_START_DATE=2025-01-15T10:30:00-05:00

# CLI override
python sync.py sync --since-date 2025-01-01
python sync.py sync --since-date 2025-01-15T10:30:00
```

## Project Structure 📁

```
social-sync/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── bluesky_client.py      # Bluesky API wrapper
│   ├── mastodon_client.py     # Mastodon API wrapper
│   ├── sync_orchestrator.py   # Main sync logic
│   ├── sync_state.py          # State management
│   └── content_processor.py   # Content adaptation
├── .github/workflows/
│   └── sync.yml               # GitHub Actions workflow
├── sync.py                    # CLI entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## Troubleshooting 🐛

### Common Issues

**Authentication Failed**
- Verify your Bluesky handle and app password
- Check Mastodon instance URL and access token
- Ensure tokens have proper scopes

**Posts Not Syncing**
- Check if posts are replies or reposts (not synced by default)
- Verify posts aren't already synced (check `sync_state.json`)
- Look at logs for specific error messages

**Character Limit Issues**
- Long posts are automatically truncated
- Check processed content in logs

### Debugging

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python sync.py sync --dry-run

# Check sync state
python sync.py status

# Test connections
python sync.py test
```

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security 🔒

- **Never commit credentials** to the repository
- Use GitHub Secrets for sensitive data
- App passwords are recommended over main account passwords
- Regularly rotate access tokens

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- [AT Protocol](https://atproto.com/) and [Bluesky](https://bsky.social/) teams
- [Mastodon.py](https://github.com/halcy/Mastodon.py) library
- [atproto Python SDK](https://github.com/MarshalX/atproto) by @marshal.dev

## Support 💬

If you encounter issues or have questions:

1. Check the [Issues](../../issues) page
2. Review the troubleshooting section above
3. Create a new issue with detailed information

Happy syncing! 🎉
