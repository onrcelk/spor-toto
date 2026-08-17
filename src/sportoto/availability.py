"""Availability and lineup uncertainty adjustments."""
from __future__ import annotations

from collections.abc import Sequence


def adjust_expected_goals(home_xg: float, away_xg: float, *, home_attack_penalty: float = 0.0,
                          away_attack_penalty: float = 0.0, home_defense_penalty: float = 0.0,
                          away_defense_penalty: float = 0.0) -> tuple[float, float]:
    penalties = [home_attack_penalty, away_attack_penalty, home_defense_penalty, away_defense_penalty]
    if any(not 0.0 <= value <= 1.0 for value in penalties):
        raise ValueError("availability penalties must be between 0 and 1")
    adjusted_home = float(home_xg) * (1.0 - home_attack_penalty) * (1.0 + 0.5 * away_defense_penalty)
    adjusted_away = float(away_xg) * (1.0 - away_attack_penalty) * (1.0 + 0.5 * home_defense_penalty)
    return max(adjusted_home, 0.05), max(adjusted_away, 0.05)


def availability_uncertainty(signals: Sequence[dict[str, str]]) -> float:
    if not signals:
        return 0.0
    uncertain = sum(signal.get("status", "unknown") in {"expected", "unknown"} for signal in signals)
    return uncertain / len(signals)


__all__ = ["adjust_expected_goals", "availability_uncertainty"]
