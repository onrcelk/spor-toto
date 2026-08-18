"""Controlled model/market/score-distribution ensemble."""
from __future__ import annotations

from .dixon_coles import market_probabilities


def normalized_market_probabilities(odds: dict[str, float]) -> dict[str, float]:
    raw = {k: 1.0 / float(v) for k, v in odds.items() if float(v) > 1.0}
    total = sum(raw.values())
    if set(raw) != {"1", "X", "2"} or total <= 0:
        raise ValueError("1/X/2 odds are required")
    return {k: v / total for k, v in raw.items()}


def ensemble_probabilities(
    model: dict[str, float],
    home_xg: float,
    away_xg: float,
    market: dict[str, float] | None = None,
    model_weight: float = 0.55,
    market_weight: float = 0.30,
    dixon_weight: float = 0.15,
) -> dict[str, float]:
    weights = {"model": model_weight, "market": market_weight if market else 0.0, "dixon": dixon_weight}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("ensemble weights must have positive sum")
    dc = market_probabilities(home_xg, away_xg)["1X2"]
    components = [(model, weights["model"]), (dc, weights["dixon"])]
    if market:
        components.append((market, weights["market"]))
    return {k: sum(float(component[k]) * weight for component, weight in components) / total for k in ("1", "X", "2")}


__all__ = ["ensemble_probabilities", "normalized_market_probabilities"]
