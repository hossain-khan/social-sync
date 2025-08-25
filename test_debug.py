#!/usr/bin/env python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.content_processor import ContentProcessor

text = "Check this out!"
facets = [{
    "index": {"byteStart": 0, "byteEnd": 15},
    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": "https://example.com"}]
}]

print("Text:", repr(text))
print("Facets:", facets)

result = ContentProcessor._expand_urls_from_facets(text, facets)
print("Result:", repr(result))
print("URL in result?", "https://example.com" in result)
