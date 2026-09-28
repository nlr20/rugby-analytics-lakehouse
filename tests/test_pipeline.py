import copy
import json
import sqlite3

import pytest

from rugby_lakehouse.pipeline import quality, run, summary
from rugby_lakehouse.landing import write_landing_file
from rugby_lakehouse.transform import TRANSFORM_VERSION, normalize_match


@pytest.fixture
def fixture_match():
    return {
        "date": "2024-09-20T18:35:00.000Z", "round": 1,
        "round_type": "league", "stadium": "Example Ground", "attendance": 1000,
        "home": {"team": "Home RFC", "score": 7,
                 "lineup": {"10": {"name": "A Player"}},
                 "scores": [{"minute": 10, "type": "Try", "player": "A Player", "value": 5},
                            {"minute": 11, "type": "Conversion", "player": "A Player", "value": 2}]},
        "away": {"team": "Away RFC", "score": 3,
                 "lineup": {"9": {"name": "B Player"}},
                 "scores": [{"minute": 20, "type": "Penalty", "player": "B Player", "value": 3}]},
    }


def test_repeat_and_late_correction(fixture_match, tmp_path):
    db_path = tmp_path / "rugby.sqlite"
    bronze = tmp_path / "bronze"
    assert run([fixture_match], db_path, bronze)["changed_matches"] == 1
    assert run([fixture_match], db_path, bronze)["changed_matches"] == 0
    corrected = copy.deepcopy(fixture_match)
    corrected["date"] = "2024-09-20T19:00:00.000Z"
    corrected["away"]["score"] = 10
    corrected["away"]["scores"].append(
        {"minute": 70, "type": "Try", "player": "B Player", "value": 5})
    assert normalize_match(fixture_match)["match_id"] == normalize_match(corrected)["match_id"]
    assert run([corrected], db_path, bronze)["changed_matches"] == 1
    assert len(list(bronze.glob("*.jsonl"))) == 2
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM bronze_event").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM silver_match").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM silver_scoring_event").fetchone()[0] == 4
        assert db.execute("SELECT COUNT(*) FROM silver_player_appearance").fetchone()[0] == 2
    rows = {row["team"]: row for row in summary(db_path)}
    assert rows["Away RFC"]["wins"] == 1
    assert rows["Away RFC"]["points_for"] == 10
    assert rows["Home RFC"]["wins"] == 0
    assert quality(db_path)["fixtures_with_score_event_discrepancy"] == 1


def test_bad_records_fail_before_writing(fixture_match, tmp_path):
    broken = copy.deepcopy(fixture_match)
    broken["home"]["score"] = -1
    with pytest.raises(ValueError, match="negative"):
        run([broken], tmp_path / "rugby.sqlite", tmp_path / "bronze")
    assert not (tmp_path / "rugby.sqlite").exists()


def test_duplicate_fixture_key_rejected(fixture_match, tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        run([fixture_match, fixture_match], tmp_path / "rugby.sqlite", tmp_path / "bronze")


def test_penalty_try_and_transform_upgrade(fixture_match, tmp_path):
    match = copy.deepcopy(fixture_match)
    match["home"]["score"] = 7
    match["home"]["scores"] = [
        {"minute": 10, "type": "Penalty Try", "player": None, "value": 5}
    ]
    db_path = tmp_path / "rugby.sqlite"
    bronze = tmp_path / "bronze"
    assert run([match], db_path, bronze)["changed_matches"] == 1
    assert quality(db_path)["fixtures_with_score_event_discrepancy"] == 0
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT points FROM silver_scoring_event").fetchone()[0] == 7
        # Simulate a database processed with the older transform.
        db.execute("UPDATE silver_match SET transform_version = 1")
        db.execute("UPDATE silver_scoring_event SET points = 5")
    assert run([match], db_path, bronze)["changed_matches"] == 1
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT points FROM silver_scoring_event").fetchone()[0] == 7
        assert db.execute("SELECT COUNT(*) FROM bronze_event").fetchone()[0] == 1


def test_landing_file_keeps_raw_and_normalized_match(fixture_match, tmp_path):
    result = write_landing_file([fixture_match], tmp_path / "landing")
    target = tmp_path / "landing" / f"urc-2024-25-{result['snapshot_hash'][:12]}.jsonl"
    assert result["matches"] == 1
    envelope = json.loads(target.read_text(encoding="utf-8"))
    assert envelope["raw"] == fixture_match
    assert envelope["match"]["home_score"] == 7
    assert envelope["match"]["source_hash"] == normalize_match(fixture_match)["source_hash"]
    assert envelope["match"]["transform_version"] == TRANSFORM_VERSION
    corrected = copy.deepcopy(fixture_match)
    corrected["home"]["score"] = 8
    later = write_landing_file([corrected], tmp_path / "landing")
    assert later["landing_file"] != result["landing_file"]
    assert target.exists()

