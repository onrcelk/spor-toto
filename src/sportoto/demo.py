from __future__ import annotations

from datetime import datetime, timezone

from sportoto.features import MatchFeatures
from sportoto.model import MatchModel
from sportoto.store import PredictionStore


def demo():
    matches = [
        MatchFeatures(
            match_id=f"M{i+1}",
            home_team="A",
            away_team="B",
            league="L1",
            kickoff_iso=datetime.now(timezone.utc).isoformat(),
            home_goals_avg=1.8,
            away_goals_avg=1.2,
            home_conceded_avg=0.9,
            away_conceded_avg=1.4,
            home_form_points=7,
            away_form_points=4,
            h2h_home_win_rate=0.55,
            h2h_draw_rate=0.25,
            h2h_away_win_rate=0.2,
            home_xg_avg=1.9,
            away_xg_avg=1.1,
            is_derby=False,
            rest_days_home=6,
            rest_days_away=5,
        )
        for i in range(38)
    ]
    labels_1x2 = [0, 1, 2] * 12 + [0, 1]
    labels_ou = [1] * 28 + [0] * 10
    model = MatchModel()
    model.fit([m.to_vector() for m in matches], labels_1x2, labels_ou)
    prediction = model.predict(matches[0])
    store = PredictionStore("/root/sportoto/data/predictions.parquet")
    store.append({
        "match_id": prediction.match_id,
        "home_team": "A",
        "away_team": "B",
        "league": "L1",
        "kickoff_iso": matches[0].kickoff_iso,
        "pred_home_win": prediction.pred_home_win,
        "pred_draw": prediction.pred_draw,
        "pred_away_win": prediction.pred_away_win,
        "pred_over_2_5": prediction.pred_over_2_5,
        "pred_under_2_5": prediction.pred_under_2_5,
        "confidence": prediction.confidence,
        "created_at": prediction.created_at,
    })
    print(prediction.__dict__)


if __name__ == "__main__":
    demo()
