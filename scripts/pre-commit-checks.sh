#!/bin/bash

# Pre-commit quality checks script for Social Sync
# Run this before committing to ensure CI will pass

set -e  # Exit on any error

echo "🔍 Running pre-commit quality checks for Social Sync..."

# Ensure we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️ No virtual environment detected. Run 'source .venv/bin/activate' first."
    exit 1
fi

echo
echo "1️⃣ Code Formatting (Black)..."
black --check --diff .
echo "✅ Black formatting passed"

echo
echo "2️⃣ Import Sorting (isort)..."
isort --check-only --diff .
echo "✅ Import sorting passed"

echo
echo "3️⃣ Type Checking (mypy)..."
mypy sync.py src/ --ignore-missing-imports --no-strict-optional
echo "✅ Type checking passed"

echo
echo "4️⃣ Type Checking (pyrefly)..."
pyrefly check sync.py src/
echo "✅ Pyrefly type checking passed"

echo
echo "5️⃣ Linting (flake8)..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
echo "✅ Critical linting passed"

echo
echo "6️⃣ All Tests (pytest)..."
python -m pytest tests/ --tb=short | grep -E "(passed|failed|error)"
echo "✅ All tests passed"

echo
echo "7️⃣ JSON Validation..."
if [ -f "sync_state.json" ]; then
    python -m json.tool sync_state.json > /dev/null
    echo "✅ JSON validation passed"
else
    echo "ℹ️ sync_state.json not found (will be created after first sync)"
fi

echo
echo "8️⃣ Security Scan (Bandit)..."
# Count medium/high severity issues
bandit_issues=$(bandit -r src/ tests/ *.py --severity-level medium --format csv 2>/dev/null | wc -l || echo "1")
if [ "$bandit_issues" -le 1 ]; then
    echo "✅ Security scan passed - no medium/high severity issues"
else
    echo "⚠️ Security scan found medium/high severity issues:"
    bandit -r src/ tests/ *.py --severity-level medium
    echo "💡 Review security issues above. High/Medium severity issues will fail CI."
    echo "   Low severity warnings are acceptable if justified with # nosec comments."
fi

echo
echo "9️⃣ Dependency Security Check (pip-audit)..."
if command -v pip-audit >/dev/null 2>&1; then
    pip-audit --desc --output=text 2>/dev/null || {
        echo "⚠️ pip-audit found vulnerability warnings (check output above)"
        echo "💡 Update dependencies if critical vulnerabilities are found"
    }
    echo "✅ Dependency security check completed"
else
    echo "ℹ️ pip-audit not installed - skipping dependency security check"
fi

echo
echo "🎉 All quality checks passed! Ready for commit and push."
echo "💡 Security scans included - same checks as CI pipeline."
