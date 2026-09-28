"""Prepare a compact, validated snapshot for a Databricks volume upload."""

from pathlib import Path

from .transform import SEASON, canonical_json, digest, normalize_match


def write_landing_file(matches: list[dict], landing_dir: Path) -> dict[str, object]:
    normalized = [normalize_match(match) for match in matches]
    ids = [match["match_id"] for match in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("Source snapshot contains duplicate fixture keys")
    snapshot_hash = digest(matches)
    target = landing_dir / f"urc-{SEASON}-{snapshot_hash[:12]}.jsonl"
    landing_dir.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            for raw, match in zip(matches, normalized):
                stream.write(canonical_json({"raw": raw, "match": match}) + "\n")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"matches": len(matches), "snapshot_hash": snapshot_hash, "landing_file": str(target)}
