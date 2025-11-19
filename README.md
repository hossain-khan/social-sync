# Social Sync 🔄

[![Code Quality Validation](https://github.com/hossain-khan/social-sync/actions/workflows/validate.yml/badge.svg)](https://github.com/hossain-khan/social-sync/actions/workflows/validate.yml) [![codecov](https://codecov.io/gh/hossain-khan/social-sync/graph/badge.svg?token=LMUT124IVM)](https://codecov.io/gh/hossain-khan/social-sync) 

A Python-based tool to automatically sync posts from Bluesky to Mastodon with GitHub Actions automation.

## ✨ Features

- 🔄 **Automated Syncing**: Schedule posts sync from Bluesky to Mastodon
- 🎯 **User-Friendly Setup**: Interactive setup wizard with helpful error messages
- 🧵 **Thread Support**: Maintains conversation threading for reply posts  
- 🚀 **GitHub Actions**: Run automatically via CI/CD workflows
- 🎯 **Smart Deduplication**: Prevents duplicate posts across sync runs
- 🚫 **Selective Sync**: Skip posts with `#no-sync` tag to control what gets synced
- 🔍 **Smart Filtering**: Filters out replies to others, reposts, and quotes of other people's content
- 📝 **Content Processing**: Handles links, images, and self-quoted posts
- 🧪 **Dry Run Mode**: Test functionality without actual posting

## 🚀 Quick Start

### For Fork Users
**👥 Setting up your own instance?** → [Fork Setup Guide](docs/FORK_SETUP.md)

**🔧 First time setup:**
```bash
# Interactive setup wizard
python sync.py setup

# Or manual setup:
cp .env.example .env
# Edit .env with your credentials
```

### For Contributors  
**🛠️ Local development?** → [Contributing Guide](docs/CONTRIBUTING.md)

## 📖 Usage

### Command Line

<img src="https://github.com/user-attachments/assets/78d49bf8-d71e-432f-b00d-010d171f9de7" align="right" width="350" alt="CLI help preview" />

```bash
# Interactive setup wizard (first time)
python sync.py setup

# Sync posts (dry run first)
python sync.py sync --dry-run
python sync.py sync

# Check configuration and test connections
python sync.py config
python sync.py test
```

### GitHub Actions
- **Automated**: Runs every 6 hours (00:00, 06:00, 12:00, 18:00 UTC) via [cron schedule](.github/workflows/sync.yml)
- **Manual**: Actions → Social Sync → Run workflow
  - Optional: Enable "Run in dry-run mode" to test without posting
- **Logs**: Check Actions tab for execution details

## ⚙️ Configuration

### Environment Variables
```bash
# Bluesky Credentials
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password

# Mastodon Credentials  
MASTODON_API_BASE_URL=https://your-instance.social
MASTODON_ACCESS_TOKEN=your-access-token
```

### Key Settings
- `SYNC_START_DATE`: Date to start syncing from (default: 7 days ago)
- `MAX_POSTS_PER_SYNC`: Maximum posts per sync run (default: 10)
- `DRY_RUN`: Test mode without posting (default: false)
- `DISABLE_SOURCE_PLATFORM`: Disable source attribution (default: false)

📚 **Full setup details:** [Setup Guide](docs/SETUP.md)

## 📋 Documentation

| Topic | Description |
|-------|-------------|
| [**Setup Guide**](docs/SETUP.md) | Complete installation and configuration |
| [**Fork Setup**](docs/FORK_SETUP.md) | Guide for forking and personal instances |
| [**API Documentation**](docs/API.md) | Client APIs and integration details |
| [**Threading**](docs/THREADING_IMPLEMENTATION.md) | How conversation threading works |
| [**Edge Case Analysis**](docs/EDGE_CASE_ANALYSIS.md) | Comprehensive analysis of 15 API edge cases |
| [**Edge Case Quick Reference**](docs/EDGE_CASE_QUICK_REFERENCE.md) | At-a-glance summary of known edge cases |
| [**Contributing**](docs/CONTRIBUTING.md) | Development workflow and standards |
| [**Testing**](docs/TESTING.md) | Test suite and validation procedures |
| [**Changelog**](docs/CHANGELOG.md) | Version history and release notes |
| [**Project Summary**](docs/PROJECT_SUMMARY.md) | Architecture and design overview |

## 🔧 How It Works

1. **Connect** to Bluesky and Mastodon APIs
2. **Fetch** recent posts from Bluesky feed  
3. **Process** content (adapt links, images, threading)
4. **Filter** duplicates and `#no-sync` tagged posts using sync state tracking
5. **Post** to Mastodon with proper threading
6. **Save** sync state for next run

**🧵 Threading:** Reply posts maintain conversation context across platforms.

**🚫 Selective Sync:** Add `#no-sync` to any Bluesky post to prevent it from syncing. The tag is case-insensitive (`#No-Sync`, `#NO-SYNC`, etc. all work).

## 🐛 Common Issues

**GitHub Actions Failing?**
- Repository rule violations → Use Personal Access Token
- Missing secrets → Check repository secrets configuration
- Branch protection → See [Setup Guide](docs/SETUP.md#branch-protection--ci-setup)

**Posts Not Syncing?**
- Run `python sync.py setup` for first-time configuration
- Verify credentials and API access with `python sync.py test`
- Check for reply/repost filtering
- Review logs for specific errors

**🔍 Full troubleshooting:** [Setup Guide](docs/SETUP.md#troubleshooting)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Follow code quality standards: [Contributing Guide](docs/CONTRIBUTING.md)
4. Run tests: `python -m pytest`
5. Submit pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [AT Protocol](https://atproto.com/) and [Bluesky](https://bsky.social/) teams
- [Mastodon.py](https://github.com/halcy/Mastodon.py) library
- [atproto Python SDK](https://github.com/MarshalX/atproto)

---

**Need help?** Check [Issues](../../issues) or create a new one with details.

**Happy syncing! 🎉**
