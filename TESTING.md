# Testing Infrastructure for Social Sync

This document describes the comprehensive test suite implemented for Social Sync.

## Overview

The Social Sync project now includes a robust testing infrastructure with multiple types of tests:

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions with mocked external dependencies
- **Threading Tests**: Specific tests for conversation threading functionality
- **CLI Tests**: Test command-line interface functionality

## Test Structure

```
social-sync/
├── tests/                      # Main test directory (pytest)
│   ├── __init__.py            # Test package initialization
│   ├── test_config.py         # Configuration management tests
│   ├── test_content_processor.py  # Content processing tests
│   ├── test_sync_state.py     # State management tests
│   ├── test_sync_orchestrator.py  # Sync orchestration tests
│   ├── test_bluesky_client.py # Bluesky client tests
│   └── test_cli.py           # CLI interface tests
├── test_integration.py        # Integration tests (standalone)
├── test_threading.py         # Threading-specific tests (standalone)
├── test_setup.py            # Original setup validation script
├── run_tests.py             # Comprehensive test runner
└── pytest.ini              # Pytest configuration
```

## Running Tests

### All Tests (Recommended)
```bash
python run_tests.py
```

### Specific Test Suites
```bash
# Unit tests only
python run_tests.py unit

# Integration tests only  
python run_tests.py integration

# Threading tests only
python run_tests.py threading

# Setup validation only
python run_tests.py validation
```

### Using pytest directly
```bash
# Run all unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_content_processor.py -v

# Run specific test method
pytest tests/test_content_processor.py::TestContentProcessor::test_truncate_if_needed_long_text -v
```

## Test Coverage

The test suite covers the following key areas:

### Unit Tests (tests/ directory)

**Configuration Management (`test_config.py`)**
- Settings validation with environment variables
- Default value handling
- Type conversion (bool, int, datetime)
- Error handling for invalid configurations
- Sync start date parsing

**Content Processing (`test_content_processor.py`)**
- Text truncation for character limits
- Hashtag and mention extraction
- URL extraction and expansion
- Embed handling (links, images, quotes)
- Sync attribution addition
- Cross-platform content transformation

**Sync State (`test_sync_state.py`)**
- State file creation and loading
- Post tracking and duplicate detection
- Parent post lookup for threading
- State persistence and recovery
- JSON validation and error handling
- Cleanup of old records

**Sync Orchestrator (`test_sync_orchestrator.py`)**
- Client setup and authentication
- Post fetching and filtering
- Individual post synchronization
- Threading logic and parent lookup
- Dry-run mode behavior
- Error handling and recovery
- Complete sync workflow

**Bluesky Client (`test_bluesky_client.py`)**
- Authentication handling
- Post fetching with date filtering
- AT Protocol data extraction
- Embed processing
- Blob downloading for images
- Thread detection and parsing

**CLI Interface (`test_cli.py`)**
- Command-line argument parsing
- Subcommand functionality
- Help text generation
- Error handling
- Integration with core functionality

### Integration Tests (`test_integration.py`)

- End-to-end sync workflow
- Component interaction verification
- State persistence across instances
- Configuration integration
- Content processing pipeline

### Threading Tests (`test_threading.py`)

- Parent-reply post sequence synchronization
- Parent post lookup functionality
- Orphaned reply handling
- Threading in dry-run mode
- Edge cases in thread detection

## Test Configuration

### pytest Configuration (`pytest.ini`)
```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-config", 
    "--strict-markers",
    "-ra"
]
```

### Coverage Configuration (`pyproject.toml`)
- Source code coverage tracking
- Exclusion of test files and virtual environments
- HTML report generation
- Coverage threshold enforcement (80%)

## Mocking Strategy

The test suite uses extensive mocking to isolate components:

- **External API calls**: Bluesky and Mastodon APIs are mocked
- **File I/O operations**: State file operations use temporary files
- **Network requests**: HTTP requests are mocked for reliability
- **Environment variables**: Test-specific environment setups

## GitHub Actions Integration

The CI/CD pipeline includes comprehensive testing:

1. **Unit Tests**: Run with pytest and coverage reporting
2. **Integration Tests**: Verify component interactions
3. **Threading Tests**: Validate conversation threading
4. **Code Quality**: Black, isort, flake8, mypy validation
5. **Security Scanning**: Bandit and dependency vulnerability checks

## Test Data Management

- **Temporary Files**: Tests use temporary directories for state files
- **Mock Data**: Realistic test data structures based on actual API responses
- **Test Credentials**: Safe test values that don't require real API access
- **Cleanup**: Automatic cleanup of test artifacts

## Coverage Goals

The test suite aims for:
- **>80% code coverage** overall
- **100% coverage** for critical paths (authentication, posting, state management)
- **Comprehensive error scenario testing**
- **Edge case handling validation**

## Adding New Tests

When adding new features:

1. **Add unit tests** in `tests/test_<module>.py`
2. **Update integration tests** if components interact
3. **Add threading tests** if threading logic changes
4. **Update CLI tests** for new commands
5. **Run full test suite** to ensure no regressions

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `TestClassName` 
- Test methods: `test_method_description_scenario`

Example:
```python
class TestContentProcessor:
    def test_truncate_if_needed_long_text(self):
        """Test that long text is properly truncated"""
```

## Troubleshooting Tests

### Common Issues

**Import Errors**
- Ensure `src/` is in Python path
- Check virtual environment activation
- Verify dependencies are installed

**Test Failures**
- Check mock configurations
- Verify test data matches expected formats
- Review environment variable setup

**Coverage Issues**
- Ensure all code paths are tested
- Add tests for error conditions
- Check exclusion patterns in configuration

### Debugging Tests

```bash
# Run with more verbose output
pytest tests/ -v -s

# Run single test with debugging
pytest tests/test_content_processor.py::TestContentProcessor::test_specific_function -v -s --pdb

# Check coverage for specific file
pytest tests/test_content_processor.py --cov=src.content_processor --cov-report=term-missing
```

## Future Improvements

Planned enhancements to the test suite:

1. **Performance Tests**: Measure sync execution times
2. **Load Tests**: Test with large numbers of posts  
3. **API Integration Tests**: Optional tests with real API credentials
4. **Property-Based Testing**: Generate test cases automatically
5. **Mutation Testing**: Verify test quality with code mutations

## Contributing

When contributing to the test suite:

1. Follow existing test patterns and naming conventions
2. Include both positive and negative test cases
3. Mock external dependencies appropriately
4. Update documentation for new test categories
5. Ensure tests run consistently across environments
