"""Audit dry-run: prove the audit pipeline works end-to-end on a REAL past
week using football-data.co.uk final scores (free, no key).

We take the last 15 matches of the 2324 Super Lig season from our own frame,
predict them with the production model, then join the REAL final scores from
football-data.co.uk and measure hit/miss. This is exactly what the cron job
will do on 2026-08-25 for the live 21-25 Aug list (but with real API-Sports /
The Odds API results once those matches finish).
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sportoto.odds import fetch_fdccouk_results
from sportoto.identity import resolve_team
from sportoto.train_superlig import build_frame as build_sl_frame

RAW = "data/live/api_sports_superlig_2022_2024.json"
LAST_N = 8
FEATURE_COLS = [
    "home_goals_avg", "away_goals_avg", "home_conceded_avg", "away_conceded_avg",
    "home_form_points", "away_form_points", "h2h_home_win_rate", "h2h_draw_rate",
    "h2h_away_win_rate", "home_xg_avg", "away_xg_avg", "is_derby",
    "rest_days_home", "rest_days_away", "elo_diff",
]


def main() -> int:
    df = build_sl_frame()
    df = df.sort_values("kickoff_iso").reset_index(drop=True)
    df["y"] = df["actual_1x2"].astype(int)

    # last 15 matches of the frame = our "prediction week"
    week = df.tail(15).copy()
    train = df.iloc[:-15]
    Xtr = train[FEATURE_COLS].to_numpy(dtype=float)
    ytr = train["y"].to_numpy(dtype=int)
    clf = Pipeline([("sc", StandardScaler()), ("clf", GradientBoostingClassifier(
        loss="log_loss", n_estimators=180, max_depth=3, learning_rate=0.05, random_state=42))])
    clf.fit(Xtr, ytr)

    preds = []
    for _, r in week.iterrows():
        feats = r[FEATURE_COLS].to_numpy(dtype=float).reshape(1, -1)
        proba = clf.predict_proba(feats)[0]
        classes = clf.named_steps["clf"].classes_
        dmap = {int(c): float(v) for c, v in zip(classes, proba)}
        pick = int(max(dmap, key=dmap.get))
        label = {0: "1", 1: "X", 2: "2"}[pick]
        preds.append({"home_team": r["home_team"], "away_team": r["away_team"],
                      "predicted_1x2": label, "actual_y": int(r["y"])})

    # real results from football-data.co.uk 2324 T1
    real = fetch_fdccouk_results("2324", "T1")
    real_by = {}
    for rr in real:
        key = (resolve_team(rr["home_team"]), resolve_team(rr["away_team"]))
        real_by[key] = rr

    hit = 0; total = 0
    for p in preds:
        key = (resolve_team(p["home_team"]), resolve_team(p["away_team"]))
        rr = real_by.get(key)
        if not rr:
            continue
        total += 1
        actual = {0: "1", 1: "X", 2: "2"}[0 if rr["home_goals"] > rr["away_goals"]
                  else (2 if rr["home_goals"] < rr["away_goals"] else 1)]
        ok = (actual == p["predicted_1x2"])
        hit += int(ok)
        print(f"  {p['home_team'][:18]:18} - {p['away_team'][:18]:18} => "
              f"tahmin {p['predicted_1x2']} | gerçek {actual} | {'HIT' if ok else 'miss'}")

    acc = hit/total if total else 0
    print(f"\nAUDIT (2324 T1 son 15 maç, gerçek sonuçlarla): {hit}/{total} HIT | acc={acc:.3f}")
    print("(Bu, 25 Ağu sonrası cron'un canlı liste için yapacağı audit'in provasıdır.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
