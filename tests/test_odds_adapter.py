import pytest

from sportoto.adapter_contracts import AdapterRegistry
from sportoto.odds_adapter import OddsAdapter, normalize_odds
from sportoto.odds_providers import TelegramStaticOddsProvider


def test_normalize_odds_keeps_raw_and_vig_removed_probabilities():
    result = normalize_odds({"1": 2.0, "X": 3.0, "2": 4.0})
    assert result["market_available"] is True
    assert result["raw_implied"]["1"] == pytest.approx(.5)
    assert sum(result["normalized_probability"].values()) == pytest.approx(1.0)
    assert result["overround"] > 1


def test_incomplete_odds_are_evidence_but_not_verified_market():
    adapter = OddsAdapter(TelegramStaticOddsProvider([{"match_id": "M04", "odds": {"1": 1.72, "X": None, "2": 5.2}, "freshness": "fresh"}]))
    result = adapter.retrieve("M04", {})
    assert result.status == "success"
    assert result.evidence[0].verified is False
    assert result.evidence[0].details["market_available"] is False


def test_timeout_is_retrieval_failure_without_evidence():
    adapter = OddsAdapter(TelegramStaticOddsProvider([]))
    result = adapter.retrieve("M04", {})
    assert result.status == "unavailable"
    assert result.evidence == ()
