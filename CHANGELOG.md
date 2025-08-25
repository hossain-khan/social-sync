# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 🧪 **Comprehensive Test Infrastructure**: Complete testing framework with 90+ unit tests covering all major components
  - pytest-based testing with coverage reporting (60% baseline coverage)
  - Test runner script (`run_tests.py`) with multiple test categories (unit, integration, threading)
  - Comprehensive testing documentation (`TESTING.md`)
  - GitHub Actions CI integration for automated testing
  - Mock-based testing to avoid external API calls during testing
  - Environment isolation and proper test configuration management

- 🧵 **Thread Support**: Maintain conversation threading when syncing reply posts from Bluesky to Mastodon
  - Reply posts are automatically detected and synced as proper Mastodon replies

### Fixed
- 🔗 **Duplicate Link Bug**: Fixed issue where links could appear twice in synced posts
  - When both facets (URL expansion) and external embeds exist for the same URL, prevent duplicate links
  - Added comprehensive test coverage for link duplication scenarios
  - Removed problematic sync state entry `3lx5slbb6zc2l` that exhibited this bug
  - Parent post lookup functionality preserves conversation context across platforms
  - Smart attribution handling (skips "(via Bluesky)" for replies to keep them concise)
  - Comprehensive logging for threading operations and debugging
  - Graceful fallback to standalone posts when parent posts aren't found in sync history

### Technical Details
- Enhanced `SyncOrchestrator.sync_post()` with thread detection logic
- Added `SyncState.get_mastodon_id_for_bluesky_post()` for parent post lookups
- Complete test coverage for configuration, sync state, content processing, clients, and CLI
- pytest configuration with coverage thresholds and HTML reporting
- Test environment setup with proper Python package imports and mocking strategies
- Updated Mastodon client integration to support `in_reply_to_id` parameter
- Thread processing maintains chronological order for proper conversation flow

## [1.0.0] - 2025-08-24

### Added
- Initial release of Social Sync
- Automated Bluesky to Mastodon post synchronization
- GitHub Actions integration with scheduled runs
- Smart deduplication to prevent duplicate posts
- Content processing for links, images, and quoted posts
- Comprehensive state management with JSON validation
- External link embedding with metadata extraction
- Character limit optimization for cross-platform compatibility
- Dry run mode for testing
- Secure credential management via GitHub Secrets

### Features
- **AT Protocol Integration**: Full Bluesky API support with authentication
- **Mastodon API Wrapper**: Complete Mastodon posting and media upload capabilities
- **Content Adaptation**: Handles character limits, link cards, images, and quotes
- **State Persistence**: Prevents duplicates across CI runs with caching
- **Fork Detection**: Automatic setup for new users forking the repository
- **Code Quality**: Comprehensive validation with Black, isort, mypy, flake8, bandit
- **JSON Validation**: Automated syntax and structure validation for sync state
- **Security Scanning**: Dependency vulnerability checks with pip-audit and safety

### Documentation
- Complete setup guide for local development and GitHub Actions
- Fork setup instructions for new users
- Troubleshooting guide and configuration reference
- Code quality standards and development guidelines
