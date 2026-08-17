"""Dixon-Coles score posterior and derived football markets."""
from __future__ import annotations

import math
from itertools import product


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def _tau(home: int, away: int, home_xg: float, away_xg: float, rho: float) -> float:
    if home == 0 and away == 0:
        return 1.0 - home_xg * away_xg * rho
    if home == 0 and away == 1:
        return 1.0 + home_xg * rho
    if home == 1 and away == 0:
        return 1.0 + away_xg * rho
    if home == 1 and away == 1:
        return 1.0 - rho
    return 1.0


def score_distribution(home_xg: float, away_xg: float, max_goals: int = 7, rho: float = -0.1) -> dict[tuple[int, int], float]:
    home_xg = max(float(home_xg), 0.01)
    away_xg = max(float(away_xg), 0.01)
    raw = {
        (home, away): _poisson(home, home_xg) * _poisson(away, away_xg) * _tau(home, away, home_xg, away_xg, rho)
        for home, away in product(range(max_goals + 1), repeat=2)
    }
    total = sum(raw.values())
    return {score: probability / total for score, probability in raw.items()}


def market_probabilities(home_xg: float, away_xg: float, max_goals: int = 7, rho: float = -0.1) -> dict[str, dict[str, float] | float]:
    dist = score_distribution(home_xg, away_xg, max_goals=max_goals, rho=rho)
    home = sum(p for (h, a), p in dist.items() if h > a)
    draw = sum(p for (h, a), p in dist.items() if h == a)
    away = sum(p for (h, a), p in dist.items() if h < a)
    over = sum(p for (h, a), p in dist.items() if h + a > 2)
    btts = sum(p for (h, a), p in dist.items() if h > 0 and a > 0)
    return {
        "1X2": {"1": home, "X": draw, "2": away},
        "over_2.5": over,
        "under_2.5": 1.0 - over,
        "btts_yes": btts,
        "btts_no": 1.0 - btts,
        "score_distribution": dist,
    }


__all__ = ["market_probabilities", "score_distribution"]
