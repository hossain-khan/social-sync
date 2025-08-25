# Social Sync Project Instructions

This is a Python 3.13+ social media synchronization tool that cross-posts between Bluesky and Mastodon.

## Code Quality Requirements

Before committing any code changes, you MUST run these formatting and validation steps in order:

1. **Format code with Black**: Always run `black src/ tests/` to ensure proper code formatting
2. **Sort imports with isort**: Always run `isort src/ tests/` to maintain consistent import ordering  
3. **Type check with mypy**: Run `mypy src/ tests/` to catch type annotation issues
4. **Lint with flake8**: Run `flake8 src/ tests/` to check code quality and style
5. **Validate JSON files**: Run `python -m json.tool sync_state.json > /dev/null` to validate JSON syntax
6. **Update CHANGELOG.md**: Document any new features, bug fixes, or breaking changes in the changelog

## Changelog Management

Always update `CHANGELOG.md` when making changes:

- **New Features**: Add to the `[Unreleased]` section under `### Added`
- **Bug Fixes**: Add to the `[Unreleased]` section under `### Fixed`
- **Breaking Changes**: Add to the `[Unreleased]` section under `### Changed`
- **Deprecations**: Add to the `[Unreleased]` section under `### Deprecated`
- **Removals**: Add to the `[Unreleased]` section under `### Removed`
- **Security Updates**: Add to the `[Unreleased]` section under `### Security`

Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format for consistency.

## JSON File Standards

The project includes JSON configuration and state files that must be properly formatted:

- **sync_state.json** - Contains sync history and state data
  - Must have valid JSON syntax
  - Required fields: `last_sync_time`, `synced_posts`, `last_bluesky_post_uri`
  - Each post in `synced_posts` must have: `bluesky_uri`, `mastodon_id`, `synced_at`
- **Format JSON files**: Use `python format_json.py` to format all JSON files, or `python format_json.py file.json` for specific files
- **Validate JSON syntax**: Use `python -m json.tool file.json > /dev/null` to check for errors
- **Manual formatting**: Use `python -m json.tool file.json > formatted.json && mv formatted.json file.json`

## Project Structure

- `src/` - Main source code directory
- `sync.py` - CLI entry point for the sync tool
- `sync_state.json` - Sync history and state persistence (tracked in git)
- `CHANGELOG.md` - Project changelog following Keep a Changelog format
- `src/config.py` - Configuration management with Pydantic models
- `src/bluesky_client.py` - AT Protocol client for Bluesky integration
- `src/mastodon_client.py` - Mastodon API client wrapper
- `src/sync_orchestrator.py` - Main sync logic coordinator with threading support
- `src/sync_state.py` - State persistence for preventing duplicates and parent post lookups
- `src/content_processor.py` - Content transformation utilities
- `src/content_processor.py` - Content transformation utilities

## Key Features

- **Cross-platform Sync**: Bluesky to Mastodon post synchronization
- **Thread Support**: Maintains conversation threading when syncing reply posts
- **Duplicate Prevention**: State-based tracking prevents re-posting content
- **Content Processing**: Handles external links, images, quoted posts, and threading
- **External Link Embedding**: Extracts and formats link metadata for cross-platform compatibility
- **JSON Validation**: Comprehensive validation system for sync state integrity

## Development Guidelines

We use Python virtual environments (.venv) and follow these conventions:

- Type hints are required for all function signatures
- Use Pydantic for configuration and data validation
- Handle API errors gracefully with proper logging
- State management prevents duplicate posts across sync runs
- Follow PEP 8 style guidelines enforced by Black and flake8

## Testing and CI

The project has GitHub Actions workflows that validate:
- Code formatting (Black)
- Import sorting (isort) 
- Type checking (mypy)
- Linting (flake8)
- JSON validation and structure verification
- Security scanning (bandit)
- Dependency vulnerability checks (pip-audit)

All code must pass these checks before merging.

## API Integration

- **Bluesky**: Uses AT Protocol SDK for post fetching and publishing
  - Handles reply detection through AT Protocol thread structure
  - Extracts parent post URIs from `reply_to` fields
- **Mastodon**: Uses mastodon.py library for API interactions
  - Supports threaded posts via `in_reply_to_id` parameter
  - Maintains conversation context across platforms
- Both clients include authentication, error handling, and rate limiting considerations
- State management tracks Bluesky-to-Mastodon post ID mappings for thread reconstruction
