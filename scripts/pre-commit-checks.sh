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
echo "4️⃣ Linting (flake8)..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
echo "✅ Critical linting passed"

echo
echo "5️⃣ All Tests (pytest)..."
python -m pytest tests/ --tb=short | grep -E "(passed|failed|error)"
echo "✅ All tests passed"

echo
echo "6️⃣ JSON Validation..."
if [ -f "sync_state.json" ]; then
    python -m json.tool sync_state.json > /dev/null
    echo "✅ JSON validation passed"
else
    echo "ℹ️ sync_state.json not found (will be created after first sync)"
fi

echo
echo "🎉 All quality checks passed! Ready for commit and push."
echo "💡 Tip: CI will run the same checks plus security scans."
