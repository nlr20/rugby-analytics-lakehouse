"""Command line entry point."""

import argparse
import json
from pathlib import Path

from .landing import write_landing_file
from .pipeline import quality, run, summary
from .source import read_matches


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the URC analytics lakehouse locally")
    parser.add_argument("command", choices=("sync", "summary", "quality", "prepare-landing"))
    parser.add_argument("--input", type=Path, help="Local source JSON; sync fetches upstream when omitted")
    parser.add_argument("--source-ref", default="master", help="Upstream commit SHA for a fixed snapshot (default: master)")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    database = args.data_dir / "rugby.sqlite"
    if args.command == "sync":
        result = run(read_matches(args.input, args.source_ref), database, args.data_dir / "bronze")
    elif args.command == "prepare-landing":
        result = write_landing_file(
            read_matches(args.input, args.source_ref), args.data_dir / "landing"
        )
    elif args.command == "summary":
        result = summary(database)
    else:
        result = quality(database)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

