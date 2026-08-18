import pytest

from sportoto.ensemble import ensemble_probabilities, normalized_market_probabilities


def test_normalized_market_probabilities_sum_to_one():
    p = normalized_market_probabilities({"1": 2.0, "X": 3.0, "2": 4.0})
    assert sum(p.values()) == pytest.approx(1.0)
    assert p["1"] > p["2"]


def test_ensemble_preserves_three_outcomes():
    p = ensemble_probabilities({"1": .6, "X": .2, "2": .2}, 1.6, .8)
    assert set(p) == {"1", "X", "2"}
    assert sum(p.values()) == pytest.approx(1.0)


def test_invalid_odds_rejected():
    with pytest.raises(ValueError):
        normalized_market_probabilities({"1": 2.0, "X": 3.0})
