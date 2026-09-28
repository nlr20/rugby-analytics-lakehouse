"""Read the upstream rugby union season snapshot."""

import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_REF = "master"
SEASONS = ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26")


def source_file(season: str) -> str:
    if season not in SEASONS:
        raise ValueError(f"Unsupported season {season!r}; choose from {', '.join(SEASONS)}")
    start = season[:4]
    return f"json/celtic-{start}-{int(start) + 1}.json"


def read_matches(path: Path | None = None, source_ref: str = SOURCE_REF, season: str = "2024-25") -> list[dict]:
    source_file(season)
    if path is None:
        if source_ref != "master" and (len(source_ref) != 40 or any(c not in "0123456789abcdef" for c in source_ref)):
            raise ValueError("Source ref must be 'master' or a 40-character lowercase commit SHA")
        url = f"https://raw.githubusercontent.com/transientlunatic/Rugby-Data/{source_ref}/{source_file(season)}"
        request = Request(url, headers={"User-Agent": "rugby-analytics-lakehouse/0.1"})
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    else:
        payload = path.read_bytes()
    matches = json.loads(payload)
    if not isinstance(matches, list):
        raise ValueError("Expected a JSON array of matches")
    return matches

