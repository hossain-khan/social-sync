# Contributing to Social Sync 🤝

Thank you for your interest in contributing to Social Sync! This document provides guidelines and information for contributors.

## Code of Conduct

Be respectful, inclusive, and collaborative. We're all here to make social media syncing better for everyone.

## Getting Started

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/social-sync.git
   cd social-sync
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials
   ```

4. **Run tests**
   ```bash
   python test_setup.py
   ```

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Test imports and basic functionality
   python test_setup.py
   
   # Test sync in dry-run mode
   python sync.py sync --dry-run
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**

## What Can You Contribute?

### 🐛 Bug Fixes
- Fix authentication issues
- Handle edge cases in content processing
- Improve error handling and logging
- Fix documentation errors

### ✨ New Features
- Support for additional social platforms
- Advanced content processing (media upload, threads)
- Bi-directional sync capabilities
- Custom filtering and formatting options
- Real-time sync via webhooks

### 📚 Documentation
- Improve setup instructions
- Add troubleshooting guides
- Create video tutorials
- Translate documentation

### 🧪 Testing
- Add unit tests
- Integration tests
- Performance testing
- Cross-platform testing

## Code Style Guidelines

### Python Code Style

- **Follow PEP 8** for Python code style
- **Use type hints** for function parameters and return values
- **Add docstrings** for modules, classes, and functions
- **Keep functions focused** and under 50 lines when possible
- **Use descriptive variable names**

Example:
```python
def process_bluesky_post(post: BlueskyPost, settings: Settings) -> str:
    """
    Process a Bluesky post for Mastodon compatibility.
    
    Args:
        post: The Bluesky post to process
        settings: Configuration settings
        
    Returns:
        Processed text suitable for Mastodon
    """
    # Implementation here
    pass
```

### File Organization

```
social-sync/
├── src/                    # Core application code
│   ├── clients/           # Platform-specific clients
│   ├── processors/        # Content processing modules
│   └── utils/            # Utility functions
├── tests/                 # Test files
├── docs/                 # Documentation
├── examples/             # Example configurations
└── scripts/              # Utility scripts
```

### Logging Standards

- **Use appropriate log levels**:
  - `DEBUG`: Detailed debugging information
  - `INFO`: General information about program execution
  - `WARNING`: Something unexpected happened but program continues
  - `ERROR`: Serious error occurred, function failed
  - `CRITICAL`: Program may not continue

- **Include context** in log messages:
  ```python
  logger.info(f"Processing post {post.uri} from @{post.author_handle}")
  logger.error(f"Failed to authenticate with {platform}: {error}")
  ```

## Testing Guidelines

### Test Structure

- **Unit tests** for individual functions and classes
- **Integration tests** for API interactions
- **End-to-end tests** for complete sync workflows

### Writing Tests

```python
import pytest
from src.content_processor import ContentProcessor

def test_content_truncation():
    """Test that long content is properly truncated"""
    long_text = "x" * 600  # Exceeds Mastodon's 500 char limit
    result = ContentProcessor.truncate_if_needed(long_text)
    
    assert len(result) <= 500
    assert result.endswith("...")
```

### Test Environment

- Use **test credentials** that don't interfere with real accounts
- **Mock API calls** when testing in CI/CD
- **Clean up test data** after test runs

## Documentation Standards

### README Updates

When adding new features:
- Update the feature list
- Add configuration options
- Include usage examples
- Update troubleshooting section if needed

### API Documentation

- Document all public methods and classes
- Include parameter types and descriptions
- Provide usage examples
- Note any limitations or caveats

### Setup Documentation

- Keep setup instructions current
- Include screenshots where helpful
- Test instructions with fresh accounts
- Update for new platform requirements

## Submitting Changes

### Pull Request Guidelines

**PR Title Format**:
- `Add: new feature description`
- `Fix: bug description`  
- `Docs: documentation update`
- `Test: testing improvements`

**PR Description Should Include**:
- Clear description of changes
- Why the change is needed
- How to test the changes
- Any breaking changes
- Screenshots if UI is affected

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated if needed
- [ ] No hardcoded credentials or secrets
- [ ] Error handling implemented
- [ ] Logging added for debugging

### Review Process

1. **Automated checks** run (GitHub Actions)
2. **Manual code review** by maintainers
3. **Testing** on different platforms if needed
4. **Merge** after approval

## Issue Guidelines

### Bug Reports

Include:
- **Environment details** (Python version, OS, etc.)
- **Steps to reproduce** the bug
- **Expected vs actual behavior**
- **Error messages or logs**
- **Configuration** (without credentials!)

### Feature Requests

Include:
- **Use case** description
- **Proposed solution** or approach
- **Alternative solutions** considered
- **Additional context** or examples

### Questions

- Check existing documentation first
- Search existing issues
- Provide context about what you're trying to achieve

## Platform-Specific Contributions

### Adding New Social Platforms

When adding support for a new platform:

1. **Create client wrapper** in `src/clients/`
2. **Implement content processor** adaptations
3. **Add configuration options**
4. **Update orchestrator** to handle new platform
5. **Write tests** for the new integration
6. **Update documentation**

### Improving Existing Integrations

- **API updates**: Keep up with platform API changes
- **Feature parity**: Ensure consistent feature support
- **Performance optimization**: Improve API usage efficiency
- **Error handling**: Better handling of platform-specific errors

## Security Considerations

### Credentials and Secrets

- **Never commit** API keys, passwords, or tokens
- **Use environment variables** for configuration
- **Validate input** from external APIs
- **Log safely** (don't log sensitive data)

### API Security

- **Use HTTPS** for all API calls
- **Implement rate limiting** respect
- **Handle authentication errors** gracefully
- **Follow platform security guidelines**

## Getting Help

### Resources

- **Documentation**: Check the `/docs` folder
- **Examples**: Look at existing code for patterns
- **Issues**: Search existing issues for similar problems
- **Discussions**: Use GitHub Discussions for questions

### Community

- **Be patient**: Maintainers are volunteers
- **Be specific**: Provide details in questions
- **Be helpful**: Help others when you can
- **Be respectful**: Follow the code of conduct

## Recognition

Contributors will be:
- **Listed in the README** contributors section
- **Mentioned in release notes** for significant contributions
- **Credited in commits** for their work

Thank you for contributing to Social Sync! 🎉
