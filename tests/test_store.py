from pathlib import Path

from sportoto.store import PredictionStore


def test_append_and_latest(tmp_path):
    store = PredictionStore(tmp_path / "predictions.parquet")
    store.append({
        "match_id": "M1",
        "home_team": "A",
        "away_team": "B",
        "league": "L1",
        "kickoff_iso": "2026-08-13T00:00:00+00:00",
        "pred_home_win": 0.5,
        "pred_draw": 0.2,
        "pred_away_win": 0.3,
        "pred_over_2_5": 0.6,
        "pred_under_2_5": 0.4,
        "confidence": 0.5,
        "created_at": "2026-08-13T00:00:00+00:00",
    })
    latest = store.latest()
    assert len(latest) == 1
    assert latest.iloc[0]["match_id"] == "M1"
