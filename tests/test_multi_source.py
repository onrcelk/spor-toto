
import pytest

from sportoto.multi_source import (
    MatchRecord,
    fetch_api_sports,
    fetch_football_data,
    parse_openfootball,
)


def response(payload):
    return lambda request: payload


def test_parse_openfootball_normalizes_score_and_ou():
    records = parse_openfootball({
        "name": "Test League",
        "matches": [{"date": "2026-08-01", "team1": "A", "team2": "B", "score": {"ht": [1, 0], "ft": [2, 1]}}],
    }, fetched_at="2026-08-17T00:00:00Z")
    assert records == [MatchRecord("openfootball", "A-B-2026-08-01", "A", "B", "2026-08-01", 2, 1, "FINISHED", "over", "2026-08-17T00:00:00Z")]


def test_parse_openfootball_keeps_unplayed_score_null():
    record = parse_openfootball({"matches": [{"date": "2026-08-20", "team1": "A", "team2": "B"}]}, "now")[0]
    assert record.home_goals is None
    assert record.status == "SCHEDULED"
    assert record.over_under is None


def test_api_sports_normalizes_fixture():
    payload = {"response": [{"fixture": {"id": 42, "date": "2026-08-16T19:00:00+00:00", "status": {"short": "FT"}}, "teams": {"home": {"name": "A"}, "away": {"name": "B"}}, "goals": {"home": 3, "away": 0}}]}
    records = fetch_api_sports("2026-08-16", api_key="secret", opener=response(payload), fetched_at="now")
    assert records[0].source_match_id == "42"
    assert records[0].result == "1"
    assert records[0].over_under == "over"


def test_football_data_missing_score_is_not_zero():
    payload = {"matches": [{"id": 9, "utcDate": "2026-08-20T19:00:00Z", "status": "TIMED", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}, "score": {"fullTime": {"home": None, "away": None}}}]}
    records = fetch_football_data(api_token="secret", opener=response(payload), fetched_at="now")
    assert records[0].home_goals is None
    assert records[0].status == "SCHEDULED"


def test_missing_api_key_fails_clearly():
    with pytest.raises(ValueError, match="API_SPORTS_KEY"):
        fetch_api_sports("2026-08-16", api_key="", opener=response({}))
