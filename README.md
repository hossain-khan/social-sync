# Social Sync 🔄

[![Code Quality Validation](https://github.com/hossain-khan/social-sync/actions/workflows/validate.yml/badge.svg)](https://github.com/hossain-khan/social-sync/actions/workflows/validate.yml) [![codecov](https://codecov.io/gh/hossain-khan/social-sync/graph/badge.svg?token=LMUT124IVM)](https://codecov.io/gh/hossain-khan/social-sync) 

A Python-based tool to automatically sync posts from Bluesky to Mastodon with GitHub Actions automation.

## ✨ Features

- 🔄 **Automated Syncing**: Schedule posts sync from Bluesky to Mastodon
- 🧵 **Thread Support**: Maintains conversation threading for reply posts  
- 🚀 **GitHub Actions**: Run automatically via CI/CD workflows
- 🎯 **Smart Deduplication**: Prevents duplicate posts across sync runs
- 📝 **Content Processing**: Handles links, images, and quoted posts
- 🧪 **Dry Run Mode**: Test functionality without actual posting

## 🚀 Quick Start

### For Fork Users
**👥 Setting up your own instance?** → [Fork Setup Guide](docs/FORK_SETUP.md)

### For Contributors  
**🛠️ Local development?** → [Contributing Guide](docs/CONTRIBUTING.md)

## 📖 Usage

### Command Line
```bash
# Sync posts (dry run first)
python sync.py sync --dry-run
python sync.py sync

# Check status and test connections
python sync.py status
python sync.py test
```

### GitHub Actions
- **Automated**: Runs every 60 minutes via cron schedule
- **Manual**: Actions → Social Sync → Run workflow  
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

📚 **Full setup details:** [Setup Guide](docs/SETUP.md)

## 📋 Documentation

| Topic | Description |
|-------|-------------|
| [**Setup Guide**](docs/SETUP.md) | Complete installation and configuration |
| [**Fork Setup**](docs/FORK_SETUP.md) | Guide for forking and personal instances |
| [**API Documentation**](docs/API.md) | Client APIs and integration details |
| [**Threading**](docs/THREADING_IMPLEMENTATION.md) | How conversation threading works |
| [**Contributing**](docs/CONTRIBUTING.md) | Development workflow and standards |
| [**Testing**](docs/TESTING.md) | Test suite and validation procedures |
| [**Changelog**](docs/CHANGELOG.md) | Version history and release notes |
| [**Project Summary**](docs/PROJECT_SUMMARY.md) | Architecture and design overview |

## 🔧 How It Works

1. **Connect** to Bluesky and Mastodon APIs
2. **Fetch** recent posts from Bluesky feed  
3. **Process** content (adapt links, images, threading)
4. **Filter** duplicates using sync state tracking
5. **Post** to Mastodon with proper threading
6. **Save** sync state for next run

**🧵 Threading:** Reply posts maintain conversation context across platforms.

## 🐛 Common Issues

**GitHub Actions Failing?**
- Repository rule violations → Use Personal Access Token
- Missing secrets → Check repository secrets configuration
- Branch protection → See [Setup Guide](docs/SETUP.md#branch-protection--ci-setup)

**Posts Not Syncing?**
- Verify credentials and API access
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
