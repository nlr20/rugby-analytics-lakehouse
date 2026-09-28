"""Read the upstream rugby union season snapshot."""

import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_REF = "master"
SOURCE_FILE = "json/celtic-2024-2025.json"


def read_matches(path: Path | None = None, source_ref: str = SOURCE_REF) -> list[dict]:
    if path is None:
        if source_ref != "master" and (len(source_ref) != 40 or any(c not in "0123456789abcdef" for c in source_ref)):
            raise ValueError("Source ref must be 'master' or a 40-character lowercase commit SHA")
        url = f"https://raw.githubusercontent.com/transientlunatic/Rugby-Data/{source_ref}/{SOURCE_FILE}"
        request = Request(url, headers={"User-Agent": "rugby-analytics-lakehouse/0.1"})
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    else:
        payload = path.read_bytes()
    matches = json.loads(payload)
    if not isinstance(matches, list):
        raise ValueError("Expected a JSON array of matches")
    return matches

