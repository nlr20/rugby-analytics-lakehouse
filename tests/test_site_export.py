"""Contract checks for the public-site export boundary."""

import copy

import pytest

from rugby_lakehouse.site_export import _queries, validate_bundle


def sample_bundle():
    fixture = {"match_id": "m1", "season": "2024-25", "status": "completed",
               "home_score": 12, "away_score": 10}
    return {
        "seasons": [{"season": "2024-25", "source_snapshot_hash": "snapshot",
                     "fixtures": 1, "completed": 1, "result_unavailable": 0}],
        "teams": [{"team_id": "a"}, {"team_id": "b"}],
        "fixtures": [fixture],
        "team_matches": [
            {"match_id": "m1", "season": "2024-25", "team_id": "a", "venue": "Home",
             "points_for": 12, "points_against": 10},
            {"match_id": "m1", "season": "2024-25", "team_id": "b", "venue": "Away",
             "points_for": 10, "points_against": 12},
        ],
        "team_seasons": [
            {"season": "2024-25", "team_id": "a", "team_name": "A", "played": 1},
            {"season": "2024-25", "team_id": "b", "team_name": "B", "played": 1},
        ],
        "scoring_patterns": [{"points": 17, "event_count": 4}],
    }


def test_export_checks_reconcile_but_surface_missing_event_detail():
    quality = validate_bundle(sample_bundle())
    assert quality["team_appearances"] == 2
    assert quality["score_event_points_gap"] == 5


@pytest.mark.parametrize("change", [
    lambda data: data["team_matches"].pop(),
    lambda data: data["team_matches"][0].update(points_for=13),
    lambda data: data["seasons"][0].update(completed=0),
])
def test_export_rejects_inconsistent_gold_data(change):
    data = copy.deepcopy(sample_bundle())
    change(data)
    with pytest.raises(ValueError):
        validate_bundle(data)


def test_gold_identifiers_cannot_inject_sql():
    with pytest.raises(ValueError):
        _queries("workspace; DROP TABLE x", "rugby_dbt")
