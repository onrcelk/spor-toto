from sportoto.advanced_pipeline import build_rolling_advanced_features, poisson_backtest


def test_rolling_features_use_only_previous_matches():
    rows = [
        {"date": "2026-01-01", "home": "A", "away": "B", "home_goals": 2, "away_goals": 0, "home_xg": 1.8, "away_xg": 0.4, "home_xa": 0.9, "away_xa": 0.2, "home_shots": 8, "away_shots": 3},
        {"date": "2026-01-08", "home": "A", "away": "B", "home_goals": 1, "away_goals": 1, "home_xg": 1.2, "away_xg": 0.7, "home_xa": 0.5, "away_xa": 0.3, "home_shots": 6, "away_shots": 5},
    ]
    features = build_rolling_advanced_features(rows, window=5)
    assert features[0]["home_xg_rolling"] == 0.0
    assert features[1]["home_xg_rolling"] == 1.8
    assert features[1]["away_xg_rolling"] == 0.4
    assert features[1]["home_history_count"] == 1


def test_poisson_backtest_returns_explicit_metrics():
    rows = [
        {"date": f"2026-01-{i:02d}", "home": "A", "away": "B", "home_goals": 1, "away_goals": 0, "home_xg": 1.4, "away_xg": 0.5, "home_xa": 0.4, "away_xa": 0.2, "home_shots": 6, "away_shots": 3}
        for i in range(1, 9)
    ]
    result = poisson_backtest(rows, min_history=1)
    assert result["evaluated_matches"] == 7
    assert 0.0 <= result["one_x_two_accuracy"] <= 1.0
    assert 0.0 <= result["over_2_5_accuracy"] <= 1.0
