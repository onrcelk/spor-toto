"""End-to-end demo: train-worthy evaluation of the model against REAL closing
odds from football-data.co.uk (free, no key).

For a past Super Lig season we:
1. build the 15-feature frame up to each match (walk-forward)
2. predict 1X2 with the same GBM pipeline
3. join real B365 closing odds
4. compute EV (edge) per pick and aggregate

This proves the odds integration works on real data and shows whether the
model historically found +EV picks.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sportoto.odds import fetch_fdccouk, market_vs_model
from sportoto.identity import normalize_team_name

RAW = "data/live/api_sports_superlig_2022_2024.json"
LAST_N = 8
FEATURE_COLS = [
    "home_goals_avg", "away_goals_avg", "home_conceded_avg", "away_conceded_avg",
    "home_form_points", "away_form_points", "h2h_home_win_rate", "h2h_draw_rate",
    "h2h_away_win_rate", "home_xg_avg", "away_xg_avg", "is_derby",
    "rest_days_home", "rest_days_away", "elo_diff",
]


def build_frame():
    d = json.load(open(RAW, encoding="utf-8"))
    df = pd.DataFrame(d)
    df["kickoff"] = pd.to_datetime(df["kickoff_iso"], utc=True)
    df = df.dropna(subset=["kickoff"]).sort_values("kickoff").reset_index(drop=True)
    df["y"] = df.apply(lambda r: 0 if r.home_goals > r.away_goals else (2 if r.home_goals < r.away_goals else 1), axis=1)
    return df


def main() -> int:
    df = build_frame()
    # walk-forward predictions
    team_stats: dict[str, list] = {}
    elo: dict[str, float] = {}
    g_hg = df.home_goals.mean(); g_ag = df.away_goals.mean()
    preds = []
    for _, r in df.iterrows():
        h, a = r.home_team, r.away_team
        def avg(team):
            hist = team_stats.get(team, [])
            recent = hist[-LAST_N:]
            if not recent:
                return {"g": g_hg, "c": g_ag, "p": 1.5, "x": (g_hg+g_ag)/2}
            return {"g": np.mean([x["g"] for x in recent]), "c": np.mean([x["c"] for x in recent]),
                    "p": np.mean([x["p"] for x in recent]), "x": np.mean([x["x"] for x in recent])}
        ha, aa = avg(h), avg(a)
        eh, ea = elo.get(h, 1500.0), elo.get(a, 1500.0)
        feats = [ha["g"], aa["g"], ha["c"], aa["c"], ha["p"], aa["p"], 0.5, 0.25, 0.25,
                 ha["x"], aa["x"], 0.0, 7.0, 7.0, eh-ea]
        preds.append({"home_team": h, "away_team": a, "features": feats,
                      "result": int(r.y), "home_goals": int(r.home_goals), "away_goals": int(r.away_goals)})
        tg, cg = r.home_goals, r.away_goals
        pth = 3 if tg > cg else (1 if tg == cg else 0)
        pta = 3 if cg > tg else (1 if cg == tg else 0)
        team_stats.setdefault(h, []).append({"g": tg, "c": cg, "p": pth, "x": (tg+cg)/2})
        team_stats.setdefault(a, []).append({"g": cg, "c": tg, "p": pta, "x": (tg+cg)/2})
        exph = 1/(1+10**((ea-eh)/400))
        res = 1 if tg > cg else (0.5 if tg == cg else 0)
        elo[h] = eh + 32*(res-exph); elo[a] = ea + 32*((1-res)-(1-exph))

    X = np.array([p["features"] for p in preds], dtype=float)
    y = np.array([p["result"] for p in preds], dtype=int)
    n = len(y); split = int(n*0.7)
    clf = Pipeline([("sc", StandardScaler()), ("clf", GradientBoostingClassifier(
        loss="log_loss", n_estimators=180, max_depth=3, learning_rate=0.05, random_state=42))])
    clf.fit(X[:split], y[:split])
    probs = clf.predict_proba(X[split:])
    classes = clf.named_steps["clf"].classes_
    picks = []
    for i, p in enumerate(probs):
        d = {int(c): float(v) for c, v in zip(classes, p)}
        pick = int(max(d, key=d.get))
        label = {0: "1", 1: "X", 2: "2"}[pick]
        # model probability for the chosen pick
        col = {"1": 0, "X": 1, "2": 2}[label]
        mp = d.get(col, 0.0)
        picks.append({"home_team": preds[split+i]["home_team"], "away_team": preds[split+i]["away_team"],
                      "predicted_1x2": label, "pred_home_win": d.get(0,0), "pred_draw": d.get(1,0),
                      "pred_away_win": d.get(2,0)})

    # real odds for the SAME season span (use 2324 as proxy; note: this is a
    # demonstration join — exact season alignment is approximate)
    odds = fetch_fdccouk("2324", "T1", "B365")
    joined = market_vs_model(odds, picks)
    print(f"Walk-forward tahmin: {len(picks)} maç (split@{split})")
    print(f"Gerçek oranla eşleşen: {len(joined)} maç")
    evs = [r["ev"] for r in joined if r["ev"] is not None]
    if evs:
        pos = [e for e in evs if e > 0]
        print(f"EV ortalaması: {np.mean(evs):.3f} | +EV pick sayısı: {len(pos)}/{len(evs)} "
              f"(%{100*len(pos)/len(evs):.0f})")
        print("Örnek +EV bulunanlar:")
        for r in sorted(joined, key=lambda x: (x['ev'] or -9), reverse=True)[:5]:
            if r["ev"]:
                print(f"  {r['home_team']} - {r['away_team']}: pick={r['predicted_1x2']} "
                      f"model={r['model_prob']:.2f} odds={r['odds']} EV={r['ev']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
