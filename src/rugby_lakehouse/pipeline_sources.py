"""Choose the audited local JSON snapshot for each Airflow run.

The community 2022-23 and 2025-26 files are intentionally not used: the
selected local copies contain the documented match repair and API backfill.
"""

from pathlib import Path

from .source import source_file


SOURCE_OVERRIDES = {
    "2022-23": "celtic-2022-2023-repaired.json",
    "2025-26": "celtic-2025-2026-api.json",
}


def selected_source_path(source_dir: Path, season: str) -> Path:
    """Return an existing local snapshot; never silently fetch a remote file."""
    ordinary_name = Path(source_file(season)).name
    path = Path(source_dir) / SOURCE_OVERRIDES.get(season, ordinary_name)
    if not path.is_file():
        raise FileNotFoundError(
            f"Selected source for {season} is missing: {path}. "
            "Mount the local data/source folder on the Airflow worker."
        )
    return path


def upload_landing_file(client, local_file: Path, remote_file: str) -> None:
    """Upload one JSONL snapshot with the SDK Files API's binary stream contract."""
    with Path(local_file).open("rb") as stream:
        client.files.upload(remote_file, stream, overwrite=True)
