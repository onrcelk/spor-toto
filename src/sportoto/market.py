"""Market probability, vig, EV, and line-movement utilities."""
from __future__ import annotations

from typing import Mapping


def decimal_implied_probability(decimal_odds: float) -> float:
    odds = float(decimal_odds)
    if odds <= 1.0:
        raise ValueError("decimal odds must be greater than 1")
    return 1.0 / odds


def remove_vig(odds: Mapping[str, float]) -> dict[str, float]:
    raw = {key: decimal_implied_probability(value) for key, value in odds.items()}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("odds must produce a positive implied-probability total")
    return {key: value / total for key, value in raw.items()}


def compute_ev(model_probability: float, decimal_odds: float) -> float:
    probability = float(model_probability)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("model_probability must be between 0 and 1")
    return probability * float(decimal_odds) - 1.0


def closing_line_delta(opening_odds: Mapping[str, float], closing_odds: Mapping[str, float]) -> dict[str, float]:
    opening = remove_vig(opening_odds)
    closing = remove_vig(closing_odds)
    return {key: closing[key] - opening[key] for key in opening if key in closing}


__all__ = ["closing_line_delta", "compute_ev", "decimal_implied_probability", "remove_vig"]
