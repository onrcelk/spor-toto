from sportoto.jackpot import estimate_coupon_winner_multiplier, contrarian_signal


def test_contrarian_signal_rewards_low_public_share():
    low = contrarian_signal("2", 0.55, 0.15)
    high = contrarian_signal("1", 0.55, 0.75)
    assert low.contrarian_value > high.contrarian_value
    assert low.expected_winners_multiplier > high.expected_winners_multiplier


def test_coupon_multiplier_is_conservative_and_positive():
    assert estimate_coupon_winner_multiplier([0.5] * 15) > 1
    assert estimate_coupon_winner_multiplier([]) == 1
