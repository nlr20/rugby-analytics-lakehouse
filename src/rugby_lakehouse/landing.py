"""Prepare a compact, validated snapshot for a Databricks volume upload."""

from pathlib import Path

from .transform import canonical_json, normalize_match


def write_landing_file(matches: list[dict], target: Path) -> dict[str, object]:
    normalized = [normalize_match(match) for match in matches]
    ids = [match["match_id"] for match in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("Source snapshot contains duplicate fixture keys")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            for raw, match in zip(matches, normalized):
                stream.write(canonical_json({"raw": raw, "match": match}) + "\n")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"matches": len(matches), "landing_file": str(target)}
