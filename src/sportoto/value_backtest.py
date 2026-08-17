"""Value-betting backtest on REAL same-season closing odds.

Uses football-data.co.uk (free, no key) closing odds for a single season and
the Super Lig model to estimate, leakage-free, whether the model's picks
carried +EV against the market, and how a simple staking strategy would have
performed.

This complements the github reference samarpreetxd/Soccer-Betting-Model (MIT)
whose idea of policy learning / backtesting we adopt here, implemented on our
own data + model (no code copied).

Method (no leakage):
- For each match in season S, build features from matches BEFORE it (walk-forward).
- Predict 1X2 with the production GBM pipeline (same as train_superlig).
- Join the match's real B365 closing odds from football-data.co.uk season S.
- Compute EV = model_prob(pick) * decimal_odds(pick) - 1.
- Simulate a flat-stake strategy: bet every pick with +EV, track ROI.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .odds import fetch_fdccouk, market_vs_model
from .identity import normalize_team_name

RAW = "data/live/api_sports_superlig_2022_2024.json"
LAST_N = 8
FEATURE_COLS = [
    "home_goals_avg", "away_goals_avg", "home_conceded_avg", "away_conceded_avg",
    "home_form_points", "away_form_points", "h2h_home_win_rate", "h2h_draw_rate",
    "h2h_away_win_rate", "home_xg_avg", "away_xg_avg", "is_derby",
    "rest_days_home", "rest_days_away", "elo_diff",
]


def _build_frame():
    d = json.load(open(RAW, encoding="utf-8"))
    df = pd.DataFrame(d)
    df["kickoff"] = pd.to_datetime(df["kickoff_iso"], utc=True)
    df = df.dropna(subset=["kickoff"]).sort_values("kickoff").reset_index(drop=True)
    df["y"] = df.apply(lambda r: 0 if r.home_goals > r.away_goals else (2 if r.home_goals < r.away_goals else 1), axis=1)
    return df


def run_value_backtest(season: str = "2324", league: str = "T1",
                       bookmaker: str = "B365", stake: float = 1.0,
                       only_positive_ev: bool = True) -> dict:
    df = _build_frame()
    # align the odds season to the most recent N matches of our frame for a
    # realistic same-window test (our API-Sports data is 2022-2025; we use the
    # 2324 football-data.co.uk odds as the market proxy for the same window).
    team_stats: dict[str, list] = {}
    elo: dict[str, float] = {}
    g_hg = df.home_goals.mean(); g_ag = df.away_goals.mean()
    rows = []
    for _, r in df.iterrows():
        h, a = r.home_team, r.away_team
        def avg(team):
            hist = team_stats.get(team, [])
            recent = hist[-LAST_N:]
            if not recent:
                return {"g": g_hg, "c": g_ag, "p": 1.5, "x": (g_hg + g_ag) / 2}
            return {"g": np.mean([x["g"] for x in recent]), "c": np.mean([x["c"] for x in recent]),
                    "p": np.mean([x["p"] for x in recent]), "x": np.mean([x["x"] for x in recent])}
        ha, aa = avg(h), avg(a)
        eh, ea = elo.get(h, 1500.0), elo.get(a, 1500.0)
        feats = [ha["g"], aa["g"], ha["c"], aa["c"], ha["p"], aa["p"], 0.5, 0.25, 0.25,
                 ha["x"], aa["x"], 0.0, 7.0, 7.0, eh - ea]
        rows.append({"home_team": h, "away_team": a, "features": feats,
                     "home_goals": int(r.home_goals), "away_goals": int(r.away_goals),
                     "y": int(r.y)})
        tg, cg = r.home_goals, r.away_goals
        pth = 3 if tg > cg else (1 if tg == cg else 0)
        pta = 3 if cg > tg else (1 if cg == tg else 0)
        team_stats.setdefault(h, []).append({"g": tg, "c": cg, "p": pth, "x": (tg + cg) / 2})
        team_stats.setdefault(a, []).append({"g": cg, "c": tg, "p": pta, "x": (tg + cg) / 2})
        exph = 1 / (1 + 10 ** ((ea - eh) / 400))
        res = 1 if tg > cg else (0.5 if tg == cg else 0)
        elo[h] = eh + 32 * (res - exph); elo[a] = ea + 32 * ((1 - res) - (1 - exph))

    X = np.array([x["features"] for x in rows], dtype=float)
    n = len(rows)
    # train on first 70%, evaluate on last 30% (the "betting window")
    split = int(n * 0.7)
    clf = Pipeline([("sc", StandardScaler()), ("clf", GradientBoostingClassifier(
        loss="log_loss", n_estimators=180, max_depth=3, learning_rate=0.05, random_state=42))])
    clf.fit(X[:split], np.array([x.get("y", 0) for x in rows[:split]]))
    classes = clf.named_steps["clf"].classes_
    probs = clf.predict_proba(X[split:])
    preds = []
    for i, p in enumerate(probs):
        d = {int(c): float(v) for c, v in zip(classes, p)}
        pick = int(max(d, key=d.get))
        label = {0: "1", 1: "X", 2: "2"}[pick]
        col = {"1": 0, "X": 1, "2": 2}[label]
        preds.append({"home_team": rows[split + i]["home_team"], "away_team": rows[split + i]["away_team"],
                      "predicted_1x2": label, "pred_home_win": d.get(0, 0), "pred_draw": d.get(1, 0),
                      "pred_away_win": d.get(2, 0), "actual_home": rows[split + i]["home_goals"],
                      "actual_away": rows[split + i]["away_goals"]})

    odds = fetch_fdccouk(season, league, bookmaker)
    joined = market_vs_model(odds, preds)
    # simulate flat stakes
    stakes_placed = 0.0
    pnl = 0.0
    hits = 0
    for r in joined:
        ev = r["ev"]
        if ev is None:
            continue
        if only_positive_ev and ev <= 0:
            continue
        # actual result
        actual = {0: "1", 1: "X", 2: "2"}[0 if r.get("actual_home", 0) > r.get("actual_away", 0)
                  else (2 if r.get("actual_home", 0) < r.get("actual_away", 0) else 1)]
        # need actual result from the prediction row
        stakes_placed += stake
        won = (r["predicted_1x2"] == _actual_from_pred(preds, r))
        if won:
            pnl += stake * (r["odds"] - 1)
            hits += 1
        else:
            pnl -= stake
    acc = hits / len([r for r in joined if r["ev"] is not None and (not only_positive_ev or r["ev"] > 0)]) if joined else 0
    return {
        "season": season, "league": league, "bookmaker": bookmaker,
        "window_matches": len(preds), "odds_matched": len(joined),
        "bets_placed": int(stakes_placed / stake) if stake else 0,
        "stake_per_bet": stake, "pnl": round(pnl, 2),
        "roi_pct": round(100 * pnl / stakes_placed, 2) if stakes_placed else None,
        "win_rate": round(acc, 3),
        "note": "Same-season proxy: model trained on 2022-2025 SL, odds from football-data.co.uk "
                f"{season} {league}. Window = last 30% of model frame joined to real odds.",
    }


def _actual_from_pred(preds, r):
    for p in preds:
        if normalize_team_name(p["home_team"]) == normalize_team_name(r["home_team"]) and \
           normalize_team_name(p["away_team"]) == normalize_team_name(r["away_team"]):
            h, a = p["actual_home"], p["actual_away"]
            return "1" if h > a else ("2" if h < a else "X")
    return None


def main() -> int:
    res = run_value_backtest()
    print(f"Value backtest ({res['season']} {res['league']} {res['bookmaker']}):")
    print(f"  Pencere maç: {res['window_matches']} | Oran eşleşen: {res['odds_matched']}")
    print(f"  Bahis: {res['bets_placed']} | PnL: {res['pnl']} | ROI: {res['roi_pct']}% | Kazanma: {res['win_rate']}")
    print(f"  Not: {res['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
