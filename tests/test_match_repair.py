"""Guard a one-match correction against wrong fixture or score joins."""

import copy

import pytest

from rugby_lakehouse.incrowd_source import convert_match
from rugby_lakehouse.match_repair import repair_match
from rugby_lakehouse.transform import normalize_match


def sample():
    summary = {
        "id": 271799, "date": "2022-10-08T18:35:00.000Z", "status": "result",
        "homeTeam": {"id": 1, "name": "Glasgow Warriors", "score": 5},
        "awayTeam": {"id": 2, "name": "Vodacom Bulls", "score": 0},
    }
    detail = copy.deepcopy(summary)
    detail.update({"round": 4, "roundTypeId": 1, "venue": {"name": "Scotstoun Stadium"},
                   "attendance": 1000,
                   "events": [{"teamId": 1, "type": "Try", "minute": 6, "playerId": 10}]})
    detail["homeTeam"]["players"] = [{"id": 10, "name": "A Player", "positionId": 8}]
    detail["awayTeam"]["players"] = [{"id": 20, "name": "B Player", "positionId": 9}]
    original = convert_match(summary, detail)
    for side in ("home", "away"):
        original[side]["lineup"] = {}
        original[side]["scores"] = []

    def fetch(url):
        return {"data": [summary]} if "compId=" in url else {"data": detail}

    return original, fetch


def test_repair_preserves_fixture_identity_and_other_source_data():
    original, fetch = sample()
    restored, index = repair_match([original], "2022-23", 271799, fetch=fetch)
    assert index == 0
    assert not original["home"]["scores"]
    assert len(restored[0]["home"]["scores"]) == 1
    assert len(restored[0]["home"]["lineup"]) == 1
    assert normalize_match(original, "2022-23", 0)["match_id"] == normalize_match(restored[0], "2022-23", 0)["match_id"]


def test_repair_rejects_score_conflict():
    original, fetch = sample()
    original["home"]["score"] = 7
    with pytest.raises(ValueError, match="final scores differ"):
        repair_match([original], "2022-23", 271799, fetch=fetch)
