"""Retrain the general (multi-league) model with the 15-feature schema
(added elo_diff) so it is compatible with the new MatchFeatures.

The master training parquet (data/sportoto_master_training.parquet) has the
legacy 14 columns; we add elo_diff=0.0 for all rows (a neutral default; the
general model mixes leagues where ELO is not meaningful), then refit.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PARQUET = "data/sportoto_master_training.parquet"
MODEL_OUT = "data/models/sportoto_master_model.joblib"
FEATURE_COLS = [
    "home_goals_avg", "away_goals_avg", "home_conceded_avg", "away_conceded_avg",
    "home_form_points", "away_form_points", "h2h_home_win_rate", "h2h_draw_rate",
    "h2h_away_win_rate", "home_xg_avg", "away_xg_avg", "is_derby",
    "rest_days_home", "rest_days_away", "elo_diff",
]


def main() -> int:
    df = pd.read_parquet(Path(PARQUET).expanduser())
    if "elo_diff" not in df.columns:
        df["elo_diff"] = 0.0
    X = df[FEATURE_COLS].to_numpy(dtype=float)
    y = df["actual_1x2"].to_numpy(dtype=int)
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(loss="log_loss", n_estimators=180, max_depth=3,
                                           learning_rate=0.05, random_state=42)),
    ])
    clf.fit(X, y)
    Path(MODEL_OUT).expanduser().parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, str(Path(MODEL_OUT).expanduser()))
    print(f"General model retrained on {len(df)} rows (15 features) -> {MODEL_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
