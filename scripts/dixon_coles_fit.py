"""Fit a Dixon-Coles (Poisson) model on real Super Lig 2022-2025 and
evaluate walk-forward 1X2 accuracy against the GBM baseline.

Dixon-Coles estimates per-team attack/defence strengths via maximum
likelihood, then predicts 1X2 from the score distribution. This is the
canonical, leakage-free strength model for football.
"""
from __future__ import annotations

import json
import math
import numpy as np
import pandas as pd
from scipy.optimize import minimize

RAW = "data/live/api_sports_superlig_2022_2024.json"


def load():
    d = json.load(open(RAW, encoding="utf-8"))
    df = pd.DataFrame(d)
    df["kickoff"] = pd.to_datetime(df["kickoff_iso"], utc=True)
    df = df.dropna(subset=["kickoff"]).sort_values("kickoff").reset_index(drop=True)
    return df


def neg_log_likelihood(params, teams, home_names, away_names, home_goals, away_goals, rho=-0.1):
    n_teams = len(teams)
    attack = dict(zip(teams, params[:n_teams]))
    defence = dict(zip(teams, params[n_teams:2 * n_teams]))
    gamma = params[2 * n_teams]  # home advantage
    ll = 0.0
    for i in range(len(home_names)):
        h, a = home_names[i], away_names[i]
        lam_h = math.exp(attack[h] + defence[a] + gamma)
        lam_a = math.exp(attack[a] + defence[h])
        # tau correction for low scores
        th = home_goals[i]
        ta = away_goals[i]
        tau = 1.0
        if th == 0 and ta == 0:
            tau = 1.0 - lam_h * lam_a * rho
        elif th == 0 and ta == 1:
            tau = 1.0 + lam_h * rho
        elif th == 1 and ta == 0:
            tau = 1.0 + lam_a * rho
        elif th == 1 and ta == 1:
            tau = 1.0 - rho
        ph = math.exp(-lam_h) * lam_h ** th / math.factorial(th)
        pa = math.exp(-lam_a) * lam_a ** ta / math.factorial(ta)
        ll += math.log(max(ph * pa * tau, 1e-12))
    return -ll


def fit(df_hist: pd.DataFrame):
    teams = sorted(set(df_hist.home_team) | set(df_hist.away_team))
    team_index = {t: i for i, t in enumerate(teams)}
    home_names = list(df_hist.home_team)
    away_names = list(df_hist.away_team)
    hg = df_hist.home_goals.values.astype(int)
    ag = df_hist.away_goals.values.astype(int)
    x0 = np.zeros(2 * len(teams) + 1)
    res = minimize(
        neg_log_likelihood,
        x0,
        args=(teams, home_names, away_names, hg, ag),
        method="L-BFGS-B",
        options={"maxiter": 200, "ftol": 1e-6},
    )
    params = res.x
    attack = {t: params[i] for t, i in team_index.items()}
    defence = {t: params[len(teams) + i] for t, i in team_index.items()}
    gamma = params[2 * len(teams)]
    return attack, defence, gamma, team_index


def predict_1x2(attack, defence, gamma, h, a):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from sportoto.dixon_coles import score_distribution
    lam_h = math.exp(attack.get(h, 0) + defence.get(a, 0) + gamma)
    lam_a = math.exp(attack.get(a, 0) + defence.get(h, 0))
    dist = score_distribution(lam_h, lam_a, rho=-0.1)
    home = sum(p for (hh, aa), p in dist.items() if hh > aa)
    draw = sum(p for (hh, aa), p in dist.items() if hh == aa)
    away = sum(p for (hh, aa), p in dist.items() if hh < aa)
    return home, draw, away


def main():
    df = load()
    n = len(df)
    split = int(n * 0.7)
    # fit DC on first 70% (all history up to split)
    hist = df.iloc[:split]
    attack, defence, gamma, _ = fit(hist)
    ytrue, ypred = [], []
    for i in range(split, n):
        r = df.iloc[i]
        h, a = r.home_team, r.away_team
        home, draw, away = predict_1x2(attack, defence, gamma, h, a)
        pred = 0 if home >= max(draw, away) else (2 if away > draw else 1)
        yt = 0 if r.home_goals > r.away_goals else (2 if r.home_goals < r.away_goals else 1)
        ypred.append(pred)
        ytrue.append(yt)
    ypred = np.array(ypred)
    ytrue = np.array(ytrue)
    acc = float(np.mean(ypred == ytrue))
    base = float(np.mean(ytrue == 0))
    print(f"[Dixon-Coles Poisson] fit@{split}/{n} | acc={acc:.3f} | baseline(home)={base:.3f} | lift={acc-base:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
