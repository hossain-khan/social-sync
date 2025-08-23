# Social Sync Project Instructions

This is a Python 3.13+ social media synchronization tool that cross-posts between Bluesky and Mastodon.

## Code Quality Requirements

Before committing any code changes, you MUST run these formatting and validation steps in order:

1. **Format code with Black**: Always run `black src/` to ensure proper code formatting
2. **Sort imports with isort**: Always run `isort src/` to maintain consistent import ordering  
3. **Type check with mypy**: Run `mypy src/` to catch type annotation issues
4. **Lint with flake8**: Run `flake8 src/` to check code quality and style

## Project Structure

- `src/` - Main source code directory
- `sync.py` - CLI entry point for the sync tool
- `src/config.py` - Configuration management with Pydantic models
- `src/bluesky_client.py` - AT Protocol client for Bluesky integration
- `src/mastodon_client.py` - Mastodon API client wrapper
- `src/sync_orchestrator.py` - Main sync logic coordinator
- `src/sync_state.py` - State persistence for preventing duplicates
- `src/content_processor.py` - Content transformation utilities

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
- Security scanning (bandit)
- Dependency vulnerability checks (pip-audit)

All code must pass these checks before merging.

## API Integration

- **Bluesky**: Uses AT Protocol SDK for post fetching and publishing
- **Mastodon**: Uses mastodon.py library for API interactions
- Both clients include authentication, error handling, and rate limiting considerations
