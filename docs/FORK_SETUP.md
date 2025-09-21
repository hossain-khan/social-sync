# Fork Setup Guide

## For New Users Forking This Repository

When you fork this repository, follow these steps to set it up for your own Bluesky ↔ Mastodon sync:

### 1. Clear Existing Sync State (Important!)

The forked repository contains the original author's sync state with 54+ synced posts. You need to clear this for a fresh start:

**Option A: Use the automated detection (Recommended)**
- The GitHub Actions workflow will automatically detect if you're a different user
- It compares your Bluesky DID with the DID in the sync state
- If they don't match, it automatically clears the sync state
- This happens during the "Initialize sync state for new users" step

**Option B: Manual reset**
- Delete the `sync_state.json` file from your fork
- The workflow will create a fresh one after your first sync

### 2. Configure Your Credentials

**For Local Development (Optional):**
If you want to test locally before setting up GitHub Actions:

```bash
# Clone your fork locally
git clone https://github.com/YOUR_USERNAME/social-sync.git
cd social-sync

# Install dependencies  
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Interactive setup wizard
python sync.py setup
```

The setup wizard provides helpful guidance for getting your credentials and testing the configuration.

**For GitHub Actions (Required):**
Set up the following GitHub repository secrets in your fork:
- `BLUESKY_HANDLE` - Your Bluesky handle (e.g., "yourname.bsky.social")
- `BLUESKY_PASSWORD` - Your Bluesky app password
- `MASTODON_API_BASE_URL` - Your Mastodon instance URL
- `MASTODON_ACCESS_TOKEN` - Your Mastodon API token

### 3. First Run

1. Go to Actions tab in your GitHub repository
2. Select "Social Sync" workflow
3. Click "Run workflow"
4. Check "Run in dry-run mode" for testing
5. Click "Run workflow"

### 4. Verify and Go Live

1. Check the workflow logs to ensure it found your posts
2. If dry-run looks good, run again without dry-run mode
3. The workflow will create/update `sync_state.json` and commit it automatically

### 5. Enable Scheduled Sync

The workflow is configured to run automatically every 6 hours (00:00, 06:00, 12:00, 18:00 UTC) as defined in [`.github/workflows/sync.yml`](../.github/workflows/sync.yml). No additional setup needed!

**Want to change the frequency?** Edit the `cron` schedule in the [sync.yml workflow file](../.github/workflows/sync.yml) to your preferred timing.

**Important:** For the workflow to commit sync state back to your repository, ensure you have proper branch protection setup. See the [Branch Protection & CI Setup](SETUP.md#branch-protection--ci-setup) section in the Setup Guide for detailed instructions.

## How Fork Detection Works

The workflow automatically detects forks by:
1. Authenticating with your Bluesky account to get your DID
2. Checking the DID in the existing sync state
3. If they don't match → clears sync state for fresh start
4. If they match → continues with existing state

## Troubleshooting

**"No posts found to sync"**: Make sure you have posts on Bluesky and your credentials are correct.

**"Authentication failed"**: Double-check your GitHub secrets are set correctly.

**"Fork not detected"**: The auto-detection might fail if authentication fails. Manually delete `sync_state.json` and re-run.

## What Happens After Setup

- Automated sync every 6 hours (00:00, 06:00, 12:00, 18:00 UTC) as configured in [`.github/workflows/sync.yml`](../.github/workflows/sync.yml)
- Only new posts (not already synced) will be processed
- Images, URLs, and text are all synced properly
- **Threading support**: Reply posts maintain conversation context on Mastodon
- Sync state is automatically committed back to your repository
- Full audit trail of all synced posts maintained in git history
