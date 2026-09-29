"""Command line entry point."""

import argparse
import json
from pathlib import Path

from .landing import write_landing_file
from .pipeline import quality, run, summary
from .source import SEASONS, read_matches, source_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the URC analytics lakehouse locally")
    parser.add_argument("command", choices=("sync", "summary", "quality", "prepare-landing"))
    parser.add_argument("--input", type=Path, help="Local source JSON; sync fetches upstream when omitted")
    parser.add_argument("--source-ref", default="master", help="Upstream commit SHA for a fixed snapshot (default: master)")
    seasons = parser.add_mutually_exclusive_group()
    seasons.add_argument("--season", help="Season such as 2026-27; defaults to 2024-25")
    seasons.add_argument("--all-seasons", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    if args.all_seasons and args.input:
        parser.error("--input can only be used with one --season")
    if args.all_seasons and args.command not in ("sync", "prepare-landing"):
        parser.error("--all-seasons is for sync or prepare-landing")
    selected_season = args.season or "2024-25"
    if args.season:
        try:
            source_file(args.season)
        except ValueError as exc:
            parser.error(str(exc))
    database = args.data_dir / "rugby.sqlite"
    if args.command == "sync":
        selected = SEASONS if args.all_seasons else (selected_season,)
        result = {season: run(read_matches(args.input, args.source_ref, season), database,
                              args.data_dir / "bronze", season) for season in selected}
        if not args.all_seasons:
            result = result[selected_season]
    elif args.command == "prepare-landing":
        selected = SEASONS if args.all_seasons else (selected_season,)
        result = {season: write_landing_file(read_matches(args.input, args.source_ref, season),
                                             args.data_dir / "landing", season) for season in selected}
        if not args.all_seasons:
            result = result[selected_season]
    elif args.command == "summary":
        result = summary(database, args.season)
    else:
        result = quality(database)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

