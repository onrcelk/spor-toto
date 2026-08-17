import pytest

from sportoto.market import closing_line_delta, compute_ev, decimal_implied_probability, remove_vig


def test_remove_vig_returns_probabilities_summing_to_one():
    probs = remove_vig({"1": 2.0, "X": 3.5, "2": 4.0})
    assert sum(probs.values()) == pytest.approx(1.0)
    assert set(probs) == {"1", "X", "2"}


def test_ev_uses_decimal_odds_and_model_probability():
    assert compute_ev(0.60, 2.0) == pytest.approx(0.20)
    assert decimal_implied_probability(2.0) == pytest.approx(0.5)


def test_closing_line_delta_is_explicit():
    delta = closing_line_delta({"1": 2.2, "X": 3.4, "2": 3.1}, {"1": 2.0, "X": 3.6, "2": 3.4})
    opening = remove_vig({"1": 2.2, "X": 3.4, "2": 3.1})
    closing = remove_vig({"1": 2.0, "X": 3.6, "2": 3.4})
    assert delta["1"] == pytest.approx(closing["1"] - opening["1"])
