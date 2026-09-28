"""Read the upstream rugby union season snapshot."""

import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = (
    "https://raw.githubusercontent.com/transientlunatic/Rugby-Data/"
    "master/json/celtic-2024-2025.json"
)


def read_matches(path: Path | None = None) -> list[dict]:
    if path is None:
        request = Request(SOURCE_URL, headers={"User-Agent": "rugby-analytics-lakehouse/0.1"})
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    else:
        payload = path.read_bytes()
    matches = json.loads(payload)
    if not isinstance(matches, list):
        raise ValueError("Expected a JSON array of matches")
    return matches

