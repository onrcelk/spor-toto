from sportoto.availability import adjust_expected_goals, availability_uncertainty


def test_availability_adjustment_reduces_missing_attack_and_increases_opponent_xg():
    home, away = adjust_expected_goals(1.8, 1.0, home_attack_penalty=0.25, home_defense_penalty=0.2)
    assert home < 1.8
    assert away > 1.0


def test_availability_uncertainty_counts_unconfirmed_signals():
    signals = [{"status": "confirmed"}, {"status": "expected"}, {"status": "unknown"}]
    assert availability_uncertainty(signals) == 2 / 3
