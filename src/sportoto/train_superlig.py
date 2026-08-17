"""Train the Super Lig model on real 2022-2025 data with ELO + home-advantage
features (the feature set that yielded the best walk-forward accuracy in
scripts/backtest_superlig.py).

Input : data/live/api_sports_superlig_2022_2024.json (1064 real matches)
Output: data/superlig_training_2022_2024.parquet (14 + 2 new features)
        data/models/superlig_model.joblib
Also prints walk-forward accuracy for verification.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

INPUT = "data/live/api_sports_superlig_2022_2024.json"
OUTPUT = "data/superlig_training_2022_2024.parquet"
MODEL_OUT = "data/models/superlig_model.joblib"
LAST_N = 8


def _to_ts(iso):
    return pd.to_datetime(iso, utc=True, errors="coerce")


def build_frame(input_path: str = INPUT, output: str = OUTPUT, last_n: int = LAST_N) -> pd.DataFrame:
    rows = json.loads(Path(input_path).expanduser().read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)
    df["kickoff"] = df["kickoff_iso"].map(_to_ts)
    df = df.dropna(subset=["kickoff"]).sort_values("kickoff").reset_index(drop=True)
    df["actual_1x2"] = df.apply(
        lambda r: 0 if r["home_goals"] > r["away_goals"] else (2 if r["home_goals"] < r["away_goals"] else 1), axis=1
    )

    g_home_g = df["home_goals"].mean()
    g_away_g = df["away_goals"].mean()

    team_stats: dict[str, list] = {}
    elo: dict[str, float] = {}

    def team_avg(team):
        hist = team_stats.get(team, [])
        recent = hist[-last_n:]
        if not recent:
            return {"goals": g_home_g, "conceded": g_away_g, "form": 1.5, "xg": (g_home_g + g_away_g) / 2}
        return {
            "goals": float(np.mean([h["goals"] for h in recent])),
            "conceded": float(np.mean([h["conceded"] for h in recent])),
            "form": float(np.mean([h["points"] for h in recent])),
            "xg": float(np.mean([h["xg"] for h in recent])),
        }

    out = []
    for _, r in df.iterrows():
        home, away = r["home_team"], r["away_team"]
        ha = team_avg(home)
        aa = team_avg(away)
        eh = elo.get(home, 1500.0)
        ea = elo.get(away, 1500.0)
        out.append({
            "match_id": f"sl_{len(out)}",
            "home_team": home, "away_team": away, "league": "Super Lig",
            "kickoff_iso": r["kickoff"].isoformat(),
            "home_goals_avg": ha["goals"], "away_goals_avg": aa["goals"],
            "home_conceded_avg": ha["conceded"], "away_conceded_avg": aa["conceded"],
            "home_form_points": ha["form"], "away_form_points": aa["form"],
            "h2h_home_win_rate": 0.5, "h2h_draw_rate": 0.25, "h2h_away_win_rate": 0.25,
            "home_xg_avg": ha["xg"], "away_xg_avg": aa["xg"],
            "is_derby": False, "rest_days_home": 7, "rest_days_away": 7,
            "elo_home": eh, "elo_away": ea, "elo_diff": eh - ea,
            "actual_1x2": int(r["actual_1x2"]),
        })
        tg, cg = r["home_goals"], r["away_goals"]
        pts_h = 3 if tg > cg else (1 if tg == cg else 0)
        pts_a = 3 if cg > tg else (1 if cg == tg else 0)
        xg = (tg + cg) / 2.0
        team_stats.setdefault(home, []).append({"goals": tg, "conceded": cg, "points": pts_h, "xg": xg})
        team_stats.setdefault(away, []).append({"goals": cg, "conceded": tg, "points": pts_a, "xg": xg})
        exp_h = 1 / (1 + 10 ** ((ea - eh) / 400))
        res_h = 1 if tg > cg else (0.5 if tg == cg else 0)
        elo[home] = eh + 32 * (res_h - exp_h)
        elo[away] = ea + 32 * ((1 - res_h) - (1 - exp_h))

    out_df = pd.DataFrame(out)
    Path(output).expanduser().parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(Path(output).expanduser(), index=False)
    return out_df


# feature column order must match features.MatchFeatures + 3 new ones
FEATURE_COLS = [
    "home_goals_avg", "away_goals_avg", "home_conceded_avg", "away_conceded_avg",
    "home_form_points", "away_form_points", "h2h_home_win_rate", "h2h_draw_rate",
    "h2h_away_win_rate", "home_xg_avg", "away_xg_avg", "is_derby",
    "rest_days_home", "rest_days_away", "elo_diff",
]


def walk_forward_accuracy(df: pd.DataFrame) -> float:
    n = len(df)
    split = int(n * 0.7)
    X = df[FEATURE_COLS].to_numpy(dtype=float)
    y = df["actual_1x2"].to_numpy(dtype=int)
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(loss="log_loss", n_estimators=180, max_depth=3,
                                           learning_rate=0.05, random_state=42)),
    ])
    clf.fit(X[:split], y[:split])
    preds = clf.predict(X[split:])
    return float(np.mean(preds == y[split:]))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=INPUT)
    ap.add_argument("--output", default=OUTPUT)
    ap.add_argument("--model-out", default=MODEL_OUT)
    args = ap.parse_args()
    df = build_frame(args.input, args.output)
    acc = walk_forward_accuracy(df)
    base = float((df["actual_1x2"].to_numpy() == 0).mean())
    print(f"Training frame: {len(df)} rows -> {args.output}")
    print(f"Walk-forward accuracy: {acc:.3f} (baseline home={base:.3f}, lift={acc-base:+.3f})")
    # refit on ALL data for production model
    X = df[FEATURE_COLS].to_numpy(dtype=float)
    y = df["actual_1x2"].to_numpy(dtype=int)
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(loss="log_loss", n_estimators=180, max_depth=3,
                                           learning_rate=0.05, random_state=42)),
    ])
    clf.fit(X, y)
    Path(args.model_out).expanduser().parent.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump(clf, str(Path(args.model_out).expanduser()))
    print(f"Model saved -> {args.model_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
