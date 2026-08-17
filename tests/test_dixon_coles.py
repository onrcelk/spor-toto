import pytest

from sportoto.dixon_coles import market_probabilities, score_distribution


def test_score_distribution_is_normalized_and_has_low_score_correction():
    dist = score_distribution(1.2, 0.8, max_goals=7, rho=-0.1)
    assert sum(dist.values()) == pytest.approx(1.0)
    assert dist[(1, 1)] > 0


def test_market_probabilities_share_one_posterior():
    probs = market_probabilities(1.4, 1.0)
    assert sum(probs["1X2"].values()) == pytest.approx(1.0)
    assert probs["over_2.5"] + probs["under_2.5"] == pytest.approx(1.0)
    assert probs["btts_yes"] + probs["btts_no"] == pytest.approx(1.0)
