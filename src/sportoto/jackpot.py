"""Estimate Spor Toto jackpot value from historical winner counts and prizes."""
from __future__ import annotations

from dataclasses import dataclass
from math import comb
from typing import Iterable


@dataclass(frozen=True)
class JackpotSignal:
    predicted_pick: str
    public_share: float
    model_probability: float
    contrarian_value: float
    expected_winners_multiplier: float
    rationale: str


def public_share_from_winner_count(winner_count: int | None, total_periods: int = 335) -> float | None:
    """Historical winner counts are jackpot-level, not per-match public picks.

    This helper intentionally does not pretend they are the same thing. It gives
    a normalized rarity signal only when a caller explicitly supplies a winner
    count, useful for calibrating the jackpot layer.
    """
    if winner_count is None or winner_count < 0:
        return None
    return 1.0 - min(winner_count / max(total_periods, 1), 1.0)


def estimate_coupon_winner_multiplier(
    predicted_public_shares: Iterable[float],
    *,
    dependence_correction: float = 0.35,
) -> float:
    """Relative rarity proxy for a full 15-result coupon.

    The exact public pick distribution for each match is unavailable. Lower
    predicted public shares imply fewer matching coupons. The correction keeps
    the proxy conservative because match outcomes are not independent.
    """
    shares = [min(max(float(x), 1e-6), 1.0) for x in predicted_public_shares]
    if not shares:
        return 1.0
    log_rarity = sum(-__import__('math').log(x) for x in shares)
    return 1.0 + dependence_correction * log_rarity / len(shares)


def contrarian_signal(predicted_pick: str, model_probability: float, public_share: float) -> JackpotSignal:
    pick = predicted_pick.upper()
    value = float(model_probability) * (1.0 - float(public_share))
    multiplier = 1.0 / max(float(public_share), 0.05)
    return JackpotSignal(
        pick, float(public_share), float(model_probability), value, multiplier,
        "Model olasılığı korunurken halkın düşük seçtiği sonuç daha yüksek ikramiye değeri taşıyabilir."
    )
