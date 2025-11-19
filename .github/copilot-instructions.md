# Social Sync Project Instructions

This is a Python 3.13+ social media synchronization tool that cross-posts between Bluesky and Mastodon.

## Development Workflow

### Feature Development and Bug Fixes
For ANY new features, bug fixes, or changes:

1. **Create a new branch first**: Always create a feature branch before making changes
   ```bash
   git checkout -b feature/your-feature-name
   # OR
   git checkout -b fix/bug-description
   ```

2. **Use the pre-commit script**: Before committing and pushing, ALWAYS run the quality checks script:
   ```bash
   ./scripts/pre-commit-checks.sh
   ```
   This script runs all required quality checks (Black, isort, mypy, flake8, pytest, JSON validation) and ensures CI will pass.

3. **Commit and push**: Only commit and push after the pre-commit script passes
   ```bash
   git add .
   git commit -m "descriptive commit message"
   git push -u origin your-branch-name
   ```

4. **Create Pull Request**: Create a PR for code review and CI validation before merging to main

### Branch Naming Convention
- **Features**: `feature/feature-name` (e.g., `feature/add-twitter-support`)
- **Bug Fixes**: `fix/bug-description` (e.g., `fix/image-attachment-blob-reference`)
- **Documentation**: `docs/description` (e.g., `docs/update-readme`)
- **Refactoring**: `refactor/description` (e.g., `refactor/extract-content-processor`)

## Code Quality Requirements

Before committing any code changes, you MUST run the pre-commit quality checks:

**Recommended**: Use the automated script for all quality checks:
```bash
./scripts/pre-commit-checks.sh
```

**Manual alternative** - run these formatting and validation steps in order:

1. **Format code with Black**: Always run `black .` to ensure proper code formatting across all files
2. **Sort imports with isort**: Always run `isort .` to maintain consistent import ordering across all files
3. **Type check with mypy**: Run `mypy src/ tests/` to catch type annotation issues
4. **Lint with flake8**: Run `flake8 src/ tests/ *.py` to check code quality and style including root directory files
5. **Run tests**: Run `python -m pytest tests/` to ensure all unit tests pass
6. **Validate JSON files**: Run `python -m json.tool sync_state.json > /dev/null` to validate JSON syntax
7. **Update CHANGELOG.md**: Document any new features, bug fixes, or breaking changes in the changelog

## Changelog Management

Always update `docs/CHANGELOG.md` when making changes:

- **New Features**: Add to the `[Unreleased]` section under `### Added`
- **Bug Fixes**: Add to the `[Unreleased]` section under `### Fixed`
- **Breaking Changes**: Add to the `[Unreleased]` section under `### Changed`
- **Deprecations**: Add to the `[Unreleased]` section under `### Deprecated`
- **Removals**: Add to the `[Unreleased]` section under `### Removed`
- **Security Updates**: Add to the `[Unreleased]` section under `### Security`

Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format for consistency.

## Documentation Organization

### Documentation Structure
All documentation is organized in the `docs/` directory:

- `docs/SETUP.md` - Complete setup and configuration guide
- `docs/FORK_SETUP.md` - Guide for fork users and personal instances  
- `docs/CONTRIBUTING.md` - Development workflow and code quality standards
- `docs/TESTING.md` - Test suite documentation and validation procedures
- `docs/API.md` - Client APIs and integration details
- `docs/THREADING_IMPLEMENTATION.md` - Threading architecture and implementation
- `docs/CHANGELOG.md` - Version history and release notes
- `docs/PROJECT_SUMMARY.md` - Architecture overview and design decisions

### Documentation Guidelines
When creating or updating documentation:

1. **New docs**: Always create in `docs/` directory
2. **README.md**: Keep minimal - link to detailed docs in `docs/`
3. **Cross-references**: Use relative links to docs: `[Setup Guide](../docs/SETUP.md)`
4. **Structure**: Follow established format with clear headings and sections
5. **Examples**: Include code examples and practical usage scenarios

## Release Process

When preparing a new release, follow these steps in order:

### Pre-Release Quality Checks
1. **Run all quality checks**: `./scripts/pre-commit-checks.sh` (comprehensive automated script)
2. **Run full test suite**: `python -m pytest -v` (ensure all 248+ tests pass)
3. **Validate JSON files**: `python -m json.tool sync_state.json > /dev/null`
4. **Test CLI functionality**: `python sync.py --version` and `python sync.py sync --dry-run`

### Version Management
The project uses centralized version management following modern Python packaging standards:

1. **Update pyproject.toml**: Change `version = "X.Y.Z"` in the `[project]` section
2. **Update package __init__.py**: Change `__version__ = "X.Y.Z"` in `src/social_sync/__init__.py`
3. **Version accessibility**:
   - CLI: `python sync.py --version`
   - Programmatic: `from src.social_sync import __version__`

### Changelog Release Preparation
1. **Move [Unreleased] to versioned section in `docs/CHANGELOG.md`**:
   ```markdown
   ## [Unreleased]

   ## [X.Y.Z] - YYYY-MM-DD
   ### Added
   - Feature descriptions...
   ```
2. **Add release date** in ISO format (YYYY-MM-DD)
3. **Ensure all changes are properly categorized** under Added/Changed/Fixed/Removed/Security

### Git Release Process
1. **Commit version changes**:
   ```bash
   git add pyproject.toml src/social_sync/__init__.py docs/CHANGELOG.md
   git commit -m "🏗️ Prepare release X.Y.Z"
   ```

2. **Create annotated release tag**:
   ```bash
   git tag -a X.Y.Z -m "Release X.Y.Z: Brief description

   Major features:
   - Feature 1
   - Feature 2
   
   Bug fixes:
   - Fix 1
   - Fix 2"
   ```

3. **Push commits and tags**:
   ```bash
   git push origin main
   git push origin X.Y.Z
   ```

### Post-Release Preparation
1. **Prepare for next development cycle**:
   - Add empty `[Unreleased]` section with categories to docs/CHANGELOG.md
   - Commit: `git commit -m "📝 Prepare CHANGELOG for next development cycle"`
   - Push: `git push origin main`

### Version Numbering Guidelines
Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (X.0.0): Breaking changes or major feature additions
- **MINOR** (X.Y.0): New features, enhancements, significant improvements
- **PATCH** (X.Y.Z): Bug fixes, minor improvements, security updates

### Tag Naming Convention
- Use version numbers without 'v' prefix: `0.1.0`, `0.2.0`, `1.0.0`
- Maintain consistency with existing tags in the repository
- Example: `git tag -a 0.2.1 -m "Release 0.2.1: Bug fixes"`

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
- `src/social_sync/` - Package directory with version information
- `sync.py` - CLI entry point for the sync tool
- `pyproject.toml` - Modern Python packaging configuration with project metadata and version
- `sync_state.json` - Sync history and state persistence (tracked in git)
- `scripts/` - Utility scripts for development and troubleshooting
  - `scripts/investigate_post.py` - Debug utility to investigate why specific Bluesky posts were/weren't synced
  - `scripts/pre-commit-checks.sh` - Automated quality checks before committing
- `docs/` - Documentation directory containing all markdown files except README.md
  - `docs/CHANGELOG.md` - Project changelog following Keep a Changelog format
  - `docs/SETUP.md` - Complete setup and configuration guide
  - `docs/CONTRIBUTING.md` - Development workflow and code quality standards
  - `docs/FORK_SETUP.md` - Guide for fork users and personal instances
  - `docs/TESTING.md` - Test suite documentation
  - `docs/API.md` - Client APIs and integration details
  - `docs/THREADING_IMPLEMENTATION.md` - Threading architecture documentation
  - `docs/PROJECT_SUMMARY.md` - Architecture overview and design decisions
- `src/config.py` - Configuration management with Pydantic models
- `src/bluesky_client.py` - AT Protocol client for Bluesky integration
- `src/mastodon_client.py` - Mastodon API client wrapper
- `src/sync_orchestrator.py` - Main sync logic coordinator with threading support
- `src/sync_state.py` - State persistence for preventing duplicates and parent post lookups
- `src/content_processor.py` - Content transformation utilities

## Packaging and Version Management

The project follows modern Python packaging standards (PEP 621):

- **pyproject.toml**: Contains project metadata, dependencies, version, and build configuration
- **Centralized versioning**: Single source of truth in pyproject.toml `[project]` section
- **Package structure**: `src/social_sync/__init__.py` provides programmatic version access
- **CLI integration**: `python sync.py --version` shows current version
- **Build system**: Configured with setuptools for potential PyPI publishing

## Key Features

- **Cross-platform Sync**: Bluesky to Mastodon post synchronization
- **Thread Support**: Maintains conversation threading when syncing reply posts
- **Duplicate Prevention**: State-based tracking prevents re-posting content
- **Content Processing**: Handles external links, images, quoted posts, and threading
- **External Link Embedding**: Extracts and formats link metadata for cross-platform compatibility
- **Filtering Statistics**: Comprehensive operational visibility with detailed filtering reports
  - BlueskyFetchResult dataclass tracks filtered replies, reposts, and date-filtered posts
  - Enhanced logging shows total retrieved, filtered, and synced post counts
  - Post-sync filtering reports for monitoring and troubleshooting
- **JSON Validation**: Comprehensive validation system for sync state integrity
- **Modern CLI**: Version support with `--version` flag and comprehensive help system

## Development Guidelines

We use Python virtual environments (.venv) and follow these conventions:

- Type hints are required for all function signatures
- Use Pydantic for configuration and data validation
- Handle API errors gracefully with proper logging
- State management prevents duplicate posts across sync runs
- Follow PEP 8 style guidelines enforced by Black and flake8

### Debugging and Investigation

When investigating why a specific Bluesky post was or wasn't synced:

1. **Use the investigation script**: `python scripts/investigate_post.py <post_rkey>`
   - Extracts post record key (rkey) from Bluesky URL: `https://bsky.app/profile/user/post/RKEY`
   - Auto-loads user DID from `sync_state.json` or accepts as argument
   - Fetches full post data from AT Protocol API
   - Analyzes sync eligibility (reply, quote, root post, tags)
   - Checks sync state and skipped posts history
   - Example: `python scripts/investigate_post.py 3m5x5kzlnoc2u`

2. **Script capabilities**:
   - Detects quote posts and identifies quoted author
   - Analyzes reply threads and parent relationships
   - Checks for `#no-sync` tag presence
   - Shows embed types (external links, images, quotes)
   - Displays facets (mentions, hashtags, links)
   - Cross-references with sync state for confirmation

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
