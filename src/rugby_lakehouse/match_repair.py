"""Repair one incomplete community fixture from its detailed URC feed record."""

import argparse
import json
from pathlib import Path

from .incrowd_source import API_ROOT, COMPETITION_ID, PROVIDER, convert_match, fetch_json, save_season
from .source import source_file
from .transform import normalize_match


def repair_match(matches, season, api_match_id, fetch=fetch_json):
    """Replace exactly one matching fixture after checking identity and scores."""
    source_file(season)
    params = f"season={season[:4]}01&provider={PROVIDER}"
    index = fetch(f"{API_ROOT}?compId={COMPETITION_ID}&{params}")
    candidates = [row for row in index.get("data", []) if row.get("id") == api_match_id]
    if len(candidates) != 1:
        raise ValueError(f"Expected exactly one API summary for match {api_match_id}")
    response = fetch(f"{API_ROOT}/{api_match_id}?{params}")
    detail = response.get("data")
    if not isinstance(detail, dict):
        raise ValueError(f"No API detail for match {api_match_id}")
    replacement = convert_match(candidates[0], detail)
    replacement_key = normalize_match(replacement, season, 0)["match_id"]
    matches = list(matches)
    positions = [i for i, row in enumerate(matches)
                 if normalize_match(row, season, i)["match_id"] == replacement_key]
    if len(positions) != 1:
        raise ValueError(f"Expected exactly one source fixture for API match {api_match_id}")
    position = positions[0]
    old = matches[position]
    if (old["home"]["score"], old["away"]["score"]) != (
            replacement["home"]["score"], replacement["away"]["score"]):
        raise ValueError("API and community fixture final scores differ")
    if old["date"] != replacement["date"]:
        raise ValueError("API and community fixture dates differ")
    if any(old[side].get("scores") or old[side].get("lineup") for side in ("home", "away")):
        raise ValueError("Source fixture already has event or lineup detail")
    if any(replacement[side]["score"] != sum(
            7 if event["type"] == "Penalty Try" else event["value"]
            for event in replacement[side]["scores"]) for side in ("home", "away")):
        raise ValueError("API scoring events do not reconcile with final scores")
    matches[position] = replacement
    if len({normalize_match(row, season, i)["match_id"]
            for i, row in enumerate(matches)}) != len(matches):
        raise ValueError("The repaired season has duplicate fixture keys")
    return matches, position


def main():
    parser = argparse.ArgumentParser(description="Repair one empty match record from its URC feed detail")
    parser.add_argument("--season", required=True)
    parser.add_argument("--api-match-id", type=int, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Output must be a new file so the original source snapshot is preserved")
    matches = json.loads(args.input.read_text(encoding="utf-8"))
    repaired, position = repair_match(matches, args.season, args.api_match_id)
    digest = save_season(repaired, args.output)
    print(json.dumps({"output": str(args.output), "sha256": digest,
                      "fixtures": len(repaired), "repaired_source_index": position,
                      "api_match_id": args.api_match_id}, indent=2))


if __name__ == "__main__":
    main()
