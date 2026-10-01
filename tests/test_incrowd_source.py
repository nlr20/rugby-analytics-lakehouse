"""Checks for the direct season-feed adapter."""

import copy

import pytest

from rugby_lakehouse.incrowd_source import build_season, convert_match
from rugby_lakehouse.transform import normalize_match


@pytest.fixture
def api_match():
    summary = {
        "id": 12, "date": "2026-06-19T18:30:00.000Z", "status": "result",
        "homeTeam": {"id": 1, "name": "Leinster Rugby", "score": 7},
        "awayTeam": {"id": 2, "name": "Fidelity SecureDrive Lions", "score": 3},
    }
    detail = copy.deepcopy(summary)
    detail.update({"round": 21, "roundTypeId": 2,
                   "venue": {"name": "Croke Park"}, "attendance": 1000,
                   "events": [
                       {"teamId": 1, "type": "Try", "minute": 10, "playerId": 100},
                       {"teamId": 1, "type": "Conversion", "minute": 11, "playerId": 100},
                       {"teamId": 2, "type": "Penalty", "minute": 20, "playerId": 200},
                   ]})
    detail["homeTeam"]["players"] = [{"id": 100, "name": "A Player", "positionId": 10}]
    detail["awayTeam"]["players"] = [{"id": 200, "name": "B Player", "positionId": 9}]
    return summary, detail


def test_converted_match_can_enter_existing_pipeline(api_match):
    raw = convert_match(*api_match)
    normalized = normalize_match(raw, "2025-26", 0)
    assert normalized["status"] == "completed"
    assert normalized["round_type"] == "knockout"
    assert normalized["home_score"] == 7
    assert normalized["away_team"] == "Lions"
    assert len(normalized["players"]) == 2
    assert sum(e["points"] for e in normalized["scoring_events"]) == 10


def test_completed_season_fetch_uses_detail_and_refreshes_cache(api_match, tmp_path):
    summary, detail = api_match
    urls = []

    def fetch(url):
        urls.append(url)
        return {"data": [summary]} if "compId=" in url else {"data": detail}

    rows = build_season("2025-26", fetch=fetch, cache_dir=tmp_path, delay_seconds=0)
    assert len(rows) == 1
    assert len(urls) == 2
    assert "season=202501" in urls[0]
    build_season("2025-26", fetch=fetch, cache_dir=tmp_path, delay_seconds=0)
    assert len(urls) == 3  # Season index is fresh; unchanged match detail came from cache.
    build_season("2025-26", fetch=fetch, cache_dir=tmp_path,
                 delay_seconds=0, refresh_cache=True)
    assert len(urls) == 5


def test_rejects_stale_detail_score(api_match):
    summary, detail = api_match
    detail["homeTeam"]["score"] = 8
    with pytest.raises(ValueError, match="inconsistent home score"):
        convert_match(summary, detail)
