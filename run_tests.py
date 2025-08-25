#!/usr/bin/env python3
"""
Test runner for Social Sync

This script runs the test suite and provides a simple interface for testing.
"""
import os
import sys
import subprocess
from pathlib import Path


def run_pytest():
    """Run tests using pytest"""
    print("🧪 Running Social Sync Test Suite...")
    print("=" * 50)

    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Set up environment for tests
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    # Run pytest with coverage
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-ra"]

    # Add coverage if pytest-cov is available
    try:
        import pytest_cov  # noqa: F401

        cmd.extend(
            ["--cov=src", "--cov-report=term-missing", "--cov-report=html:htmlcov"]
        )
        print("📊 Coverage reporting enabled")
    except ImportError:
        print("⚠️  pytest-cov not found, running without coverage")

    print(f"Running command: {' '.join(cmd)}")
    print()

    # Run tests with proper environment
    result = subprocess.run(cmd, env=env)

    if result.returncode == 0:
        print("\n✅ All tests passed!")
        if os.path.exists("htmlcov/index.html"):
            print(f"📊 Coverage report: {Path('htmlcov/index.html').absolute()}")
    else:
        print("\n❌ Some tests failed!")

    return result.returncode


def run_integration_tests():
    """Run integration tests"""
    print("🔗 Running Integration Tests...")
    print("=" * 30)

    # Run integration tests
    cmd = [sys.executable, "test_integration.py"]
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("✅ Integration tests passed!")
    else:
        print("❌ Integration tests failed!")

    return result.returncode


def run_threading_tests():
    """Run threading-specific tests"""
    print("🧵 Running Threading Tests...")
    print("=" * 30)

    # Run threading tests
    cmd = [sys.executable, "test_threading.py"]
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("✅ Threading tests passed!")
    else:
        print("❌ Threading tests failed!")

    return result.returncode


def run_validation_tests():
    """Run the original validation script"""
    print("🔍 Running Setup Validation...")
    print("=" * 30)

    # Set test credentials to avoid validation failures
    test_env = os.environ.copy()
    test_env.update(
        {
            "BLUESKY_HANDLE": "test.bsky.social",
            "BLUESKY_PASSWORD": "test-password",
            "MASTODON_ACCESS_TOKEN": "test-token-12345",
            "MASTODON_API_BASE_URL": "https://mastodon.social",
        }
    )

    # Run validation without actually connecting to APIs
    cmd = [sys.executable, "test_setup.py"]
    result = subprocess.run(cmd, env=test_env)

    if result.returncode == 0:
        print("✅ Setup validation passed!")
    else:
        print("❌ Setup validation failed!")

    return result.returncode


def main():
    """Main test runner"""
    print("🚀 Social Sync Test Runner")
    print("=" * 50)

    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()

        if test_type == "unit":
            return run_pytest()
        elif test_type == "integration":
            return run_integration_tests()
        elif test_type == "threading":
            return run_threading_tests()
        elif test_type == "validation":
            return run_validation_tests()
        elif test_type == "all":
            pass  # Run all tests below
        else:
            print(f"Unknown test type: {test_type}")
            print("Available options: unit, integration, threading, validation, all")
            return 1

    # Run all tests by default
    results = []

    # 1. Unit tests with pytest
    print("\n" + "=" * 60)
    results.append(run_pytest())

    # 2. Integration tests
    print("\n" + "=" * 60)
    results.append(run_integration_tests())

    # 3. Threading tests
    print("\n" + "=" * 60)
    results.append(run_threading_tests())

    # 4. Setup validation (if credentials allow)
    if not any(
        var in os.environ for var in ["BLUESKY_HANDLE", "MASTODON_ACCESS_TOKEN"]
    ):
        print("\n" + "=" * 60)
        print("⚠️  Skipping setup validation (no credentials)")
    else:
        print("\n" + "=" * 60)
        results.append(run_validation_tests())

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    failed_count = sum(1 for r in results if r != 0)
    total_count = len(results)

    if failed_count == 0:
        print(f"🎉 All {total_count} test suites PASSED!")
        return 0
    else:
        print(f"💥 {failed_count}/{total_count} test suites FAILED!")
        return 1


if __name__ == "__main__":
    exit(main())
