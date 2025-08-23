# Setup Guide for Social Sync

This guide walks you through setting up Social Sync to automatically sync your Bluesky posts to Mastodon.

## Quick Start Checklist ✅

- [ ] Bluesky account with app password created
- [ ] Mastodon account with API access token
- [ ] GitHub repository forked and secrets configured
- [ ] Tested locally (optional but recommended)

## Step 1: Bluesky Setup

### Create App Password

1. **Log in to Bluesky** via web browser
2. **Go to Settings** → **App Passwords**
3. **Click "Add App Password"**
4. **Name it** something like "Social Sync"
5. **Copy the generated password** (you can't see it again!)
6. **Note your handle** (e.g., `john.bsky.social`)

### Important Notes
- ⚠️ **Save the app password immediately** - you can't retrieve it later
- 🔒 **App passwords are safer** than using your main password
- 📝 **Your handle** is what appears after the @ symbol

## Step 2: Mastodon Setup

### Create API Application

1. **Log in to your Mastodon instance**
2. **Go to Preferences** → **Development** → **New Application**
3. **Fill out the form:**
   - **Application name**: "Social Sync"
   - **Website**: Your GitHub repository URL (optional)
   - **Scopes**: Select `write:statuses` (required for posting)
4. **Submit** and **click on your application name**
5. **Copy the Access Token**
6. **Note your instance URL** (e.g., `https://mastodon.social`)

### Supported Instances
- ✅ mastodon.social
- ✅ mastodon.world  
- ✅ fosstodon.org
- ✅ Any Mastodon-compatible instance

## Step 3: GitHub Setup

### Fork the Repository

1. **Visit** the [Social Sync repository](https://github.com/your-username/social-sync)
2. **Click "Fork"** in the top-right corner
3. **Choose your account** as the destination

### Configure Secrets

1. **Go to your forked repository**
2. **Click "Settings"** tab
3. **Select "Secrets and variables"** → **"Actions"**
4. **Add the following secrets:**

| Secret Name | Value | Example |
|-------------|-------|---------|
| `BLUESKY_HANDLE` | Your Bluesky handle | `john.bsky.social` |
| `BLUESKY_PASSWORD` | Your Bluesky app password | `abcd-1234-efgh-5678` |
| `MASTODON_API_BASE_URL` | Your Mastodon instance URL | `https://mastodon.social` |
| `MASTODON_ACCESS_TOKEN` | Your Mastodon access token | `abc123def456...` |

### Add Each Secret:
1. **Click "New repository secret"**
2. **Enter the name** (exactly as shown above)
3. **Paste the value**
4. **Click "Add secret"**

## Step 4: Test the Setup

### Enable GitHub Actions

1. **Go to the "Actions" tab** in your repository
2. **Click "I understand my workflows, go ahead and enable them"**
3. **Find "Social Sync" workflow**
4. **Click "Run workflow"** → Select **"Enable dry run"** → **"Run workflow"**

### Check the Results

1. **Wait for the workflow to complete** (usually 1-2 minutes)
2. **Click on the workflow run** to see details
3. **Check the logs** for any errors
4. **Look for**: "✅ Sync completed successfully!"

## Step 5: Customize Settings (Optional)

You can customize the sync behavior by adding these optional secrets:

| Secret Name | Default | Description |
|-------------|---------|-------------|
| `MAX_POSTS_PER_SYNC` | 10 | Maximum posts to sync per run |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Step 6: Local Development (Optional)

If you want to run and test locally:

### Setup Local Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/social-sync.git
cd social-sync

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### Configure Local Environment

Edit `.env` file:

```bash
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password
MASTODON_API_BASE_URL=https://your-instance.social
MASTODON_ACCESS_TOKEN=your-access-token
DRY_RUN=true
LOG_LEVEL=DEBUG
```

### Test Locally

```bash
# Test connections
python sync.py test

# Test sync (dry run)
python sync.py sync --dry-run

# Check status
python sync.py status
```

## Troubleshooting Common Issues

### ❌ "Failed to authenticate with Bluesky"

**Possible causes:**
- Incorrect handle format (should include `.bsky.social`)
- Wrong app password
- App password was regenerated/deleted

**Solution:**
- Double-check your handle: `yourname.bsky.social`
- Generate a new app password if needed
- Update GitHub secrets

### ❌ "Failed to authenticate with Mastodon"

**Possible causes:**
- Incorrect instance URL
- Invalid access token
- Insufficient permissions

**Solution:**
- Verify instance URL format: `https://instance.social`
- Ensure access token has `write:statuses` scope
- Regenerate access token if needed

### ❌ "No new posts to sync"

**This is normal if:**
- You haven't posted on Bluesky recently
- Posts were already synced
- Posts are replies/reposts (not synced)

### ❌ GitHub Actions not running

**Check:**
- Actions are enabled in your repository
- Secrets are properly configured
- Repository is not archived/disabled

## Security Best Practices

- 🔒 **Never share your app passwords or tokens**
- 🔄 **Rotate credentials periodically**
- 👀 **Monitor your account activity**
- 🚫 **Don't commit credentials to git**
- ✅ **Use GitHub Secrets for sensitive data**

## Getting Help

If you're still having issues:

1. **Check the logs** in GitHub Actions
2. **Try dry-run mode** first
3. **Verify all credentials** are correct
4. **Open an issue** with error details

## What Happens Next?

Once setup is complete:

- 🕒 **Automatic syncing** every 15 minutes
- 📱 **New Bluesky posts** appear on Mastodon
- 📊 **Activity logs** available in GitHub Actions
- 🔄 **Duplicate posts** are automatically prevented

Your social media presence is now synchronized! 🎉
