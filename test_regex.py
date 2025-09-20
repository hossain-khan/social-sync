#!/usr/bin/env python3
import re

# Test cases from the failing tests
test_cases = [
    ("##double", []),
    ("#hashtag#another", ["hashtag", "another"]),
    ("#hashtag", ["hashtag"]),
    ("#-invalid", ["-invalid"]),
]

# Try different patterns
patterns = [
    ("Original", r"#([^\s#]+)"),
    ("No consecutive #", r"(?<![#])#([^\s#]+)"),
]

for pattern_name, pattern_str in patterns:
    pattern = re.compile(pattern_str)
    print(f"\n{pattern_name}: {pattern_str}")
    for test_input, expected in test_cases:
        result = pattern.findall(test_input)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {test_input}: {result} (expected: {expected})")