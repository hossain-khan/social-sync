#!/usr/bin/env python3
"""
JSON Formatter for Social Sync Project

This script formats JSON files with consistent indentation and validates their syntax.
Usage: python scripts/format_json.py [file1.json] [file2.json] ...
       python scripts/format_json.py  # formats all JSON files in project
"""

import json
import sys
from pathlib import Path
from typing import List


def format_json_file(file_path: Path) -> bool:
    """
    Format a single JSON file with proper indentation.

    Args:
        file_path: Path to the JSON file

    Returns:
        True if successful, False if there were errors
    """
    try:
        # Read the original file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Write back with proper formatting
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            # Ensure file ends with newline
            f.write("\n")

        print(f"✅ Formatted: {file_path}")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ JSON syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def find_json_files() -> List[Path]:
    """Find all JSON files in the project."""
    json_files = []

    # Common JSON files in the project root
    for filename in ["sync_state.json", "package.json", "tsconfig.json"]:
        path = Path(filename)
        if path.exists():
            json_files.append(path)

    # Look for other JSON files but exclude node_modules, .git, etc.
    for path in Path(".").rglob("*.json"):
        if not any(
            part.startswith(".") or part in ["node_modules", "__pycache__"]
            for part in path.parts
        ):
            if path not in json_files:
                json_files.append(path)

    return json_files


def main():
    """Main function to format JSON files."""
    if len(sys.argv) > 1:
        # Format specific files provided as arguments
        files_to_format = [Path(arg) for arg in sys.argv[1:]]
    else:
        # Format all JSON files in the project
        files_to_format = find_json_files()

    if not files_to_format:
        print("No JSON files found to format.")
        return

    print(f"🔧 Formatting {len(files_to_format)} JSON file(s)...")

    success_count = 0
    for file_path in files_to_format:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue

        if format_json_file(file_path):
            success_count += 1

    print(
        f"\n📊 Results: {success_count}/{len(files_to_format)} files formatted successfully"
    )

    if success_count < len(files_to_format):
        sys.exit(1)


if __name__ == "__main__":
    main()
