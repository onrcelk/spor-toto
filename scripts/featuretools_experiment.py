"""Experiment: ParthK7-style automated feature engineering (no featuretools dep).

Idea borrowed from ParthK7/Soccer-Match-Outcome-Prediction- (no license; concept
only, no code copied): derive richer team features from rolling match history
beyond simple averages — add std-dev and recent-form TREND (slope) of goals.

We compare walk-forward 1X2 accuracy:
- baseline 15 features (form/xg/h2h/elo)
- + rolling std of goals + form trend slope (automated features)
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RAW = "data/live/api_sports_superlig_2022_2024.json"
LAST_N = 8


def load():
    d = json.load(open(RAW, encoding="utf-8"))
    df = pd.DataFrame(d)
    df["kickoff"] = pd.to_datetime(df["kickoff_iso"], utc=True)
    df = df.dropna(subset=["kickoff"]).sort_values("kickoff").reset_index(drop=True)
    df["y"] = df.apply(lambda r: 0 if r.home_goals > r.away_goals else (2 if r.home_goals < r.away_goals else 1), axis=1)
    return df


def team_features(hist_rows):
    if not hist_rows:
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # g_mean,g_std,a_mean,a_std,trend_h,trend_a
    g = np.array([x["g"] for x in hist_rows], dtype=float)
    a = np.array([x["c"] for x in hist_rows], dtype=float)
    g_mean, g_std = g.mean(), (g.std() if len(g) > 1 else 0.0)
    a_mean, a_std = a.mean(), (a.std() if len(a) > 1 else 0.0)
    # trend slope of goals-for over last matches (linear regression on index)
    if len(g) >= 3:
        x = np.arange(len(g))
        trend_h = float(np.polyfit(x, g, 1)[0])
        trend_a = float(np.polyfit(x, a, 1)[0])
    else:
        trend_h = trend_a = 0.0
    return [g_mean, g_std, a_mean, a_std, trend_h, trend_a]


def build(mode: str):
    df = load()
    g_hg = df.home_goals.mean(); g_ag = df.away_goals.mean()
    team_stats: dict[str, list] = {}
    elo: dict[str, float] = {}
    X, y = [], []
    for _, r in df.iterrows():
        h, a = r.home_team, r.away_team
        hf = team_features(team_stats.get(h, [])[-LAST_N:])
        af = team_features(team_stats.get(a, [])[-LAST_N:])
        eh, ea = elo.get(h, 1500.0), elo.get(a, 1500.0)
        if mode == "base":
            feats = [hf[0], af[0], hf[2], af[2], 1.5, 1.5, 0.5, 0.25, 0.25,
                     (hf[0]+hf[2])/2, (af[0]+af[2])/2, 0.0, 7.0, 7.0, eh-ea]
        else:  # auto: add std + trend
            feats = [hf[0], af[0], hf[2], af[2], 1.5, 1.5, 0.5, 0.25, 0.25,
                     (hf[0]+hf[2])/2, (af[0]+af[2])/2, 0.0, 7.0, 7.0, eh-ea,
                     hf[1], af[1], hf[3], af[3], hf[4], af[4], hf[5], af[5]]
        X.append(feats)
        y.append(int(r.y))
        tg, cg = r.home_goals, r.away_goals
        pth = 3 if tg > cg else (1 if tg == cg else 0)
        pta = 3 if cg > tg else (1 if cg == tg else 0)
        team_stats.setdefault(h, []).append({"g": tg, "c": cg})
        team_stats.setdefault(a, []).append({"g": cg, "c": tg})
        exph = 1/(1+10**((ea-eh)/400))
        res = 1 if tg > cg else (0.5 if tg == cg else 0)
        elo[h] = eh + 32*(res-exph); elo[a] = ea + 32*((1-res)-(1-exph))
    return np.array(X, dtype=float), np.array(y, dtype=int)


def evaluate(mode):
    X, y = build(mode)
    n = len(y); split = int(n*0.7)
    clf = Pipeline([("sc", StandardScaler()), ("clf", GradientBoostingClassifier(
        loss="log_loss", n_estimators=180, max_depth=3, learning_rate=0.05, random_state=42))])
    clf.fit(X[:split], y[:split])
    preds = clf.predict(X[split:])
    acc = float(np.mean(preds == y[split:]))
    base = float(np.mean(y[split:] == 0))
    print(f"[{mode}] features={X.shape[1]} | walk-forward acc={acc:.3f} | baseline(home)={base:.3f} | lift={acc-base:+.3f}")
    return acc


def main() -> int:
    evaluate("base")
    evaluate("auto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
