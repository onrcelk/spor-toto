"""Leakage-safe advanced feature engineering and Poisson backtesting."""
from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any


def _mean(values: deque[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def _elo_expected(home_elo: float, away_elo: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-(home_elo + 50.0 - away_elo) / 400.0))


def build_rolling_advanced_features(rows: list[dict[str, Any]], window: int = 5) -> list[dict[str, Any]]:
    if window < 1:
        raise ValueError("window must be at least 1")
    ordered = sorted(rows, key=lambda row: str(row.get("date", "")))
    history: dict[str, dict[str, deque[float] | float]] = defaultdict(lambda: {
        "xg_for": deque(maxlen=window), "xg_against": deque(maxlen=window),
        "xa_for": deque(maxlen=window), "shots_for": deque(maxlen=window),
        "shots_against": deque(maxlen=window), "elo": 1500.0,
    })
    result: list[dict[str, Any]] = []
    for row in ordered:
        home_name, away_name = str(row["home"]), str(row["away"])
        home, away = history[home_name], history[away_name]
        home_xg = _mean(home["xg_for"])
        away_xg = _mean(away["xg_for"])
        home_xg_allowed = _mean(home["xg_against"])
        away_xg_allowed = _mean(away["xg_against"])
        record = dict(row)
        record.update({
            "home_xg_rolling": home_xg,
            "away_xg_rolling": away_xg,
            "home_xg_allowed_rolling": home_xg_allowed,
            "away_xg_allowed_rolling": away_xg_allowed,
            "home_xa_rolling": _mean(home["xa_for"]),
            "away_xa_rolling": _mean(away["xa_for"]),
            "home_shots_rolling": _mean(home["shots_for"]),
            "away_shots_rolling": _mean(away["shots_for"]),
            "home_shot_diff_rolling": _mean(home["shots_for"]) - _mean(home["shots_against"]),
            "away_shot_diff_rolling": _mean(away["shots_for"]) - _mean(away["shots_against"]),
            "elo_home_pre": float(home["elo"]),
            "elo_away_pre": float(away["elo"]),
            "elo_diff_pre": float(home["elo"] - away["elo"]),
            "home_history_count": len(home["xg_for"]),
            "away_history_count": len(away["xg_for"]),
        })
        result.append(record)
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        home["xg_for"].append(float(row.get("home_xg", hg)))
        home["xg_against"].append(float(row.get("away_xg", ag)))
        home["xa_for"].append(float(row.get("home_xa", 0.0)))
        home["shots_for"].append(float(row.get("home_shots", 0.0)))
        home["shots_against"].append(float(row.get("away_shots", 0.0)))
        away["xg_for"].append(float(row.get("away_xg", ag)))
        away["xg_against"].append(float(row.get("home_xg", hg)))
        away["xa_for"].append(float(row.get("away_xa", 0.0)))
        away["shots_for"].append(float(row.get("away_shots", 0.0)))
        away["shots_against"].append(float(row.get("home_shots", 0.0)))
        expected = _elo_expected(float(home["elo"]), float(away["elo"]))
        actual = 1.0 if hg > ag else 0.0 if hg < ag else 0.5
        delta = 20.0 * (actual - expected)
        home["elo"] += delta
        away["elo"] -= delta
    return result


def _poisson_probability(goals: int, expected: float) -> float:
    return math.exp(-expected) * expected ** goals / math.factorial(goals)


def poisson_backtest(rows: list[dict[str, Any]], min_history: int = 3) -> dict[str, Any]:
    features = build_rolling_advanced_features(rows)
    evaluated = [row for row in features if row["home_history_count"] >= min_history and row["away_history_count"] >= min_history]
    one_x_two_hits = 0
    over_hits = 0
    for row in evaluated:
        home_lambda = max(0.15, (row["home_xg_rolling"] + row["away_xg_allowed_rolling"]) / 2.0)
        away_lambda = max(0.15, (row["away_xg_rolling"] + row["home_xg_allowed_rolling"]) / 2.0)
        matrix = {(h, a): _poisson_probability(h, home_lambda) * _poisson_probability(a, away_lambda)
                  for h in range(8) for a in range(8)}
        home_prob = sum(p for (h, a), p in matrix.items() if h > a)
        draw_prob = sum(p for (h, a), p in matrix.items() if h == a)
        away_prob = sum(p for (h, a), p in matrix.items() if h < a)
        predicted = "1" if home_prob >= draw_prob and home_prob >= away_prob else "X" if draw_prob >= away_prob else "2"
        actual = "1" if row["home_goals"] > row["away_goals"] else "X" if row["home_goals"] == row["away_goals"] else "2"
        one_x_two_hits += predicted == actual
        over_prob = sum(p for (h, a), p in matrix.items() if h + a > 2)
        predicted_ou = "over" if over_prob >= 0.5 else "under"
        actual_ou = "over" if row["home_goals"] + row["away_goals"] > 2.5 else "under"
        over_hits += predicted_ou == actual_ou
    count = len(evaluated)
    return {
        "evaluated_matches": count,
        "one_x_two_accuracy": one_x_two_hits / count if count else None,
        "over_2_5_accuracy": over_hits / count if count else None,
        "feature_window": 5,
        "leakage_policy": "features use only matches strictly before the target match",
    }


__all__ = ["build_rolling_advanced_features", "poisson_backtest"]
