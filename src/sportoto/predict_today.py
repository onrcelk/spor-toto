from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sportoto.features import MatchFeatures
from sportoto.model import MatchModel
from sportoto.analysis import analyze_match, format_analysis


MATCHES = [
    {
        "match_id": "tobol-partizan",
        "home_team": "Tobol",
        "away_team": "Partizan",
        "league": "UEFA Conference League",
        "kickoff_iso": "2026-08-13T18:00:00+00:00",
        "home_goals_avg": 1.2,
        "away_goals_avg": 2.1,
        "home_conceded_avg": 1.6,
        "away_conceded_avg": 0.8,
        "home_form_points": 4.0,
        "away_form_points": 9.0,
        "h2h_home_win_rate": 0.0,
        "h2h_draw_rate": 0.0,
        "h2h_away_win_rate": 1.0,
        "home_xg_avg": 1.1,
        "away_xg_avg": 2.0,
        "is_derby": False,
        "rest_days_home": 7,
        "rest_days_away": 7,
        "market_odds": {"home": 2.66, "draw": 2.98, "away": 1.95, "over": 1.55, "under": 1.73},
        "context": "Partizan 3-0 leading aggregate, second leg.",
    },
    {
        "match_id": "karabag-dynamo",
        "home_team": "Karabağ",
        "away_team": "Dinamo Kiev",
        "league": "UEFA Conference League",
        "kickoff_iso": "2026-08-13T19:00:00+00:00",
        "home_goals_avg": 1.8,
        "away_goals_avg": 1.5,
        "home_conceded_avg": 0.9,
        "away_conceded_avg": 0.7,
        "home_form_points": 7.0,
        "away_form_points": 7.0,
        "h2h_home_win_rate": 0.5,
        "h2h_draw_rate": 0.0,
        "h2h_away_win_rate": 0.5,
        "home_xg_avg": 1.7,
        "away_xg_avg": 1.3,
        "is_derby": False,
        "rest_days_home": 7,
        "rest_days_away": 7,
        "market_odds": {"home": 1.59, "draw": 3.17, "away": 3.54, "over": 1.62, "under": 1.65},
        "context": "First leg: Dinamo 1-0 Karabağ. Karabağ needs goal at home.",
    },
    {
        "match_id": "ilves-rijeka",
        "home_team": "Ilves",
        "away_team": "Rijeka",
        "league": "UEFA Conference League",
        "kickoff_iso": "2026-08-13T16:00:00+00:00",
        "home_goals_avg": 1.4,
        "away_goals_avg": 1.2,
        "home_conceded_avg": 1.1,
        "away_conceded_avg": 0.6,
        "home_form_points": 5.0,
        "away_form_points": 8.0,
        "h2h_home_win_rate": 0.0,
        "h2h_draw_rate": 0.0,
        "h2h_away_win_rate": 1.0,
        "home_xg_avg": 1.3,
        "away_xg_avg": 1.1,
        "is_derby": False,
        "rest_days_home": 7,
        "rest_days_away": 7,
        "market_odds": {"home": 3.93, "draw": 3.05, "away": 1.56, "over": 1.76, "under": 1.52},
        "context": "First leg: Rijeka 1-0 Ilves. Rijeka away favorite.",
    },
    {
        "match_id": "flora-inter-escaldes",
        "home_team": "Flora Tallinn",
        "away_team": "Inter Escaldes",
        "league": "UEFA Conference League",
        "kickoff_iso": "2026-08-13T17:00:00+00:00",
        "home_goals_avg": 1.3,
        "away_goals_avg": 1.1,
        "home_conceded_avg": 1.2,
        "away_conceded_avg": 0.9,
        "home_form_points": 6.0,
        "away_form_points": 8.0,
        "h2h_home_win_rate": 0.0,
        "h2h_draw_rate": 0.0,
        "h2h_away_win_rate": 1.0,
        "home_xg_avg": 1.2,
        "away_xg_avg": 1.0,
        "is_derby": False,
        "rest_days_home": 7,
        "rest_days_away": 7,
        "market_odds": {"home": 1.65, "draw": 3.10, "away": 3.36, "over": 1.56, "under": 1.71},
        "context": "First leg: Inter Escaldes 2-0 Flora Tallinn. Flora needs comeback.",
    },
]


def main() -> int:
    model = MatchModel()
    records = [
        MatchFeatures(
            match_id=f"SYN-{i}",
            home_team="A",
            away_team="B",
            league="L1",
            kickoff_iso="2026-08-13T00:00:00+00:00",
            home_goals_avg=1.5,
            away_goals_avg=1.2,
            home_conceded_avg=1.0,
            away_conceded_avg=1.1,
            home_form_points=6,
            away_form_points=4,
            h2h_home_win_rate=0.5,
            h2h_draw_rate=0.25,
            h2h_away_win_rate=0.25,
            home_xg_avg=1.5,
            away_xg_avg=1.1,
            is_derby=False,
            rest_days_home=6,
            rest_days_away=6,
        )
        for i in range(120)
    ]
    labels_1x2 = [0, 1, 2] * 40
    labels_ou = [1] * 80 + [0] * 40
    model.fit([m.to_vector() for m in records], labels_1x2, labels_ou)

    analyses = []
    for match in MATCHES:
        feature_data = {
            k: v
            for k, v in match.items()
            if k in {
                "match_id",
                "home_team",
                "away_team",
                "league",
                "kickoff_iso",
                "home_goals_avg",
                "away_goals_avg",
                "home_conceded_avg",
                "away_conceded_avg",
                "home_form_points",
                "away_form_points",
                "h2h_home_win_rate",
                "h2h_draw_rate",
                "h2h_away_win_rate",
                "home_xg_avg",
                "away_xg_avg",
                "is_derby",
                "rest_days_home",
                "rest_days_away",
            }
        }
        mf = MatchFeatures(**feature_data)
        notes = [match.get("context", "")]
        analysis = analyze_match(mf, model, notes=notes)
        analyses.append(analysis)
        print(format_analysis(analysis))
        print("-" * 60)

    out_path = Path("~/.sportoto/raw/2026-08-13-predictions.json").expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(
            [
                {
                    "match_id": a.match_id,
                    "home_team": a.home_team,
                    "away_team": a.away_team,
                    "pred_home_win": a.prediction.pred_home_win,
                    "pred_draw": a.prediction.pred_draw,
                    "pred_away_win": a.prediction.pred_away_win,
                    "pred_over_2_5": a.prediction.pred_over_2_5,
                    "pred_under_2_5": a.prediction.pred_under_2_5,
                    "confidence": a.prediction.confidence,
                    "market_odds": match.get("market_odds", {}),
                    "analyzed_at": a.analyzed_at,
                }
                for a, match in zip(analyses, MATCHES)
            ],
            fh,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Predictions saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
