"""Prevent the orchestrated run from selecting stale community snapshots."""

import pytest

from rugby_lakehouse.pipeline_sources import selected_source_path, upload_landing_file


@pytest.mark.parametrize(("season", "filename"), [
    ("2021-22", "celtic-2021-2022.json"),
    ("2022-23", "celtic-2022-2023-repaired.json"),
    ("2025-26", "celtic-2025-2026-api.json"),
    ("2026-27", "celtic-2026-2027.json"),
])
def test_selected_local_source(tmp_path, season, filename):
    (tmp_path / filename).write_text("[]", encoding="utf-8")
    assert selected_source_path(tmp_path, season) == tmp_path / filename


def test_missing_repaired_source_does_not_fall_back(tmp_path):
    (tmp_path / "celtic-2022-2023.json").write_text("[]", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="celtic-2022-2023-repaired.json"):
        selected_source_path(tmp_path, "2022-23")


def test_invalid_season_rejected(tmp_path):
    with pytest.raises(ValueError, match="consecutive"):
        selected_source_path(tmp_path, "2026-28")


def test_volume_upload_uses_binary_sdk_stream(tmp_path):
    payload = tmp_path / "season.jsonl"
    payload.write_bytes(b'{"source_snapshot_hash":"abc"}\n')
    observed = {}

    class Files:
        def upload(self, path, contents, *, overwrite):
            observed.update(path=path, payload=contents.read(), overwrite=overwrite)

    class Client:
        files = Files()

    upload_landing_file(Client(), payload, "/Volumes/workspace/rugby_analytics/landing/season.jsonl")
    assert observed == {
        "path": "/Volumes/workspace/rugby_analytics/landing/season.jsonl",
        "payload": b'{"source_snapshot_hash":"abc"}\n',
        "overwrite": True,
    }
