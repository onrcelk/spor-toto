"""Walk-forward backtest for the Super Lig model on real 2022-2025 data.

Measures true out-of-sample 1X2 accuracy and compares:
- current feature set (form/xg/h2h only, no H/A or ELO)
- with home-advantage + ELO added (proposed improvement)
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

RAW = "data/live/api_sports_superlig_2022_2024.json"
LAST_N = 8


def load() -> pd.DataFrame:
    d = json.load(open(RAW, encoding="utf-8"))
    df = pd.DataFrame(d)
    df["kickoff"] = pd.to_datetime(df["kickoff_iso"], utc=True)
    df = df.dropna(subset=["kickoff"]).sort_values("kickoff").reset_index(drop=True)
    df["y"] = df.apply(
        lambda r: 0 if r.home_goals > r.away_goals else (2 if r.home_goals < r.away_goals else 1), axis=1
    )
    return df


def build_features(df: pd.DataFrame, with_elo: bool) -> tuple[list, list, list]:
    """Walk-forward: for each match use only prior matches for features."""
    team_hist: dict[str, list] = {}
    elo: dict[str, float] = {}

    def team_avg(team, last_n=LAST_N):
        hist = team_hist.get(team, [])
        recent = hist[-last_n:]
        if not recent:
            return {
                "goals": df.home_goals.mean(),
                "conc": df.away_goals.mean(),
                "form": 1.5,
                "xg": (df.home_goals.mean() + df.away_goals.mean()) / 2,
            }
        return {
            "goals": float(np.mean([h["g"] for h in recent])),
            "conc": float(np.mean([h["c"] for h in recent])),
            "form": float(np.mean([h["p"] for h in recent])),
            "xg": float(np.mean([h["x"] for h in recent])),
        }

    X, y, meta = [], [], []
    for _, r in df.iterrows():
        home, away = r.home_team, r.away_team
        ha = team_avg(home)
        aa = team_avg(away)
        if with_elo:
            eh = elo.get(home, 1500.0)
            ea = elo.get(away, 1500.0)
            elo_diff = eh - ea
        else:
            elo_diff = 0.0
        X.append([ha["goals"], ha["conc"], ha["form"], ha["xg"],
                  aa["goals"], aa["conc"], aa["form"], aa["xg"], elo_diff])
        y.append(int(r.y))
        meta.append((home, away, int(r.y)))
        # update history + ELO
        tg, cg = r.home_goals, r.away_goals
        pts_h = 3 if tg > cg else (1 if tg == cg else 0)
        pts_a = 3 if cg > tg else (1 if cg == tg else 0)
        xg = (tg + cg) / 2.0
        team_hist.setdefault(home, []).append({"g": tg, "c": cg, "p": pts_h, "x": xg})
        team_hist.setdefault(away, []).append({"g": cg, "c": tg, "p": pts_a, "x": xg})
        if with_elo:
            eh = elo.get(home, 1500.0)
            ea = elo.get(away, 1500.0)
            exp_h = 1 / (1 + 10 ** ((ea - eh) / 400))
            elo[home] = eh + 32 * ((1 if tg > cg else (0.5 if tg == cg else 0)) - exp_h)
            elo[away] = ea + 32 * ((1 if cg > tg else (0.5 if cg == tg else 0)) - (1 - exp_h))
    return X, y, meta


def evaluate(X, y, meta, label: str):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    n = len(y)
    split = int(n * 0.7)
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(loss="log_loss", n_estimators=180, max_depth=3,
                                           learning_rate=0.05, random_state=42)),
    ])
    clf.fit(X[:split], y[:split])
    probs = clf.predict_proba(X[split:])
    classes = clf.named_steps["clf"].classes_
    preds = []
    for p in probs:
        d = {int(c): float(v) for c, v in zip(classes, p)}
        preds.append(int(max(d, key=d.get)))
    yt = y[split:]
    acc = float(np.mean([p == t for p, t in zip(preds, yt)]))
    # baseline: always predict home win (class 0)
    base = float(np.mean([0 == t for t in yt]))
    print(f"[{label}] walk-forward split@{split}/{n} | acc={acc:.3f} | baseline(home)={base:.3f} | lift={acc-base:+.3f}")
    return acc


def main() -> int:
    df = load()
    print(f"Veri: {len(df)} maç (2022-2025 gercek Super Lig)")
    dist = df["y"].value_counts(normalize=True).round(3).to_dict()
    print("1X2 dağılımı:", dist, "-> rastgele baseline ~", max(dist.get(0,0), dist.get(1,0), dist.get(2,0)))
    X1, y1, m1 = build_features(df, with_elo=False)
    evaluate(X1, y1, m1, "mevcut ozellikler (form/xg/h2h, H/A yok)")
    X2, y2, m2 = build_features(df, with_elo=True)
    evaluate(X2, y2, m2, "öneri: + ELO + H/A destegi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
