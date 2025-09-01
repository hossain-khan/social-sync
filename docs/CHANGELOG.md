# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed
- 🔧 **GitHub Actions Workflow Enhancement**: Improved error handling and token configuration for CI/CD pipeline
  - **Switched to Personal Access Token**: Now uses `PAT_TOKEN` secret for reliable branch protection bypass
  - Enhanced checkout action with PAT authentication for consistent repository access
  - Better compatibility with repositories using GitHub rulesets for branch protection
  - Simplified setup process with clear PAT creation instructions
  - More reliable than default `GITHUB_TOKEN` bypass configurations
- 📋 **Documentation Updates**: Updated documentation to reflect accurate implementation details
  - Fixed GitHub Actions schedule documentation (daily at 2:00 AM UTC, not hourly)
  - Updated Python version requirements to reflect 3.9+ compatibility
  - Corrected dependency versions to match current implementation
  - Updated technology stack references in project documentation

### Fixed
- 🛡️ **Branch Protection CI Issue**: Fixed silent failures when GitHub Actions cannot commit to protected branches
  - Workflow now properly fails with clear error messages when branch protection blocks sync state updates
  - Replaced silent success (`exit 0`) with proper failure (`exit 1`) on push errors
  - Added comprehensive error messages guiding users to configure GitHub Actions bypass
  - Prevents duplicate posts by failing fast when sync state cannot be saved
  - Includes actionable instructions for repository ruleset configuration
- 🐍 **Python 3.9 Compatibility**: Fixed type annotation compatibility for Python 3.9+
  - Replaced modern union syntax (`str | None`) with `Optional[str]` for broader Python version support
  - Added warning suppression for urllib3 OpenSSL compatibility warning on macOS systems
  - Updated project configuration to officially support Python 3.9, 3.10, 3.11, 3.12, and 3.13

## [0.3.0] - 2025-08-30

### Added
- 🧵 **Self-Reply Threading Support**: Enable syncing of Bluesky self-reply threads as properly threaded posts on Mastodon
  - Self-replies to your own posts now sync as connected thread on Mastodon instead of being filtered out
  - Maintains chronological order and parent-child relationships in thread chains
  - Added robust DID extraction from AT Protocol URIs for self-reply detection (`_extract_did_from_uri`)
  - Enhanced filtering logic to allow self-replies while continuing to filter replies from other users
  - Thread posts sync in proper sequence: parent post → reply → reply-to-reply → etc.
  - Graceful fallback: orphaned replies (missing parent) post as standalone rather than failing
  - Comprehensive test coverage including DID extraction validation and thread chain handling

### Fixed
- 🖼️ **Image Attachment Bug**: Fixed critical issue where images in Bluesky posts synced as placeholder text instead of actual media attachments
  - Images were appearing as "📷 [1 image]" text in Mastodon posts instead of proper image attachments
  - Root cause: Missing blob reference extraction in `_extract_embed_data` method
  - Enhanced `BlueskyClient._extract_embed_data()` to properly extract AT Protocol blob references needed for image downloads
  - Added comprehensive unit test `test_extract_embed_data_images_with_blob_reference` to prevent regression
  - Now correctly processes blob references like `bafkreihitajnhlutyalbqxutmfifkjxxrdqgl5basih3i7z2rjnmwpo4ya` for image download
  - Complete image sync pipeline now functions: detect → extract blob_ref → download → upload to Mastodon → attach

## [0.2.0] - 2025-08-25

### Added
- 🧪 **Comprehensive Test Infrastructure**: Complete testing framework with 120+ unit tests covering all major components
  - pytest-based testing with coverage reporting (60% baseline coverage)
  - Test runner script (`run_tests.py`) with multiple test categories (unit, integration, threading)
  - Comprehensive testing documentation (`TESTING.md`)
  - GitHub Actions CI integration for automated testing
  - Mock-based testing to avoid external API calls during testing
  - Environment isolation and proper test configuration management

- 🧵 **Thread Support**: Maintain conversation threading when syncing reply posts from Bluesky to Mastodon
  - Reply posts are automatically detected and synced as proper Mastodon replies

- 📊 **Filtering Statistics & Operational Visibility**: Enhanced logging with comprehensive filtering statistics
  - New `BlueskyFetchResult` dataclass tracks filtering statistics (replies, reposts, date-filtered posts)
  - Detailed logging reports showing total retrieved posts, filtered replies, and date-filtered posts
  - Enhanced operational visibility with post-sync filtering reports
  - Comprehensive statistics for monitoring sync behavior and troubleshooting

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

## [0.1.0] - 2025-08-23

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
