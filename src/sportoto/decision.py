"""Deterministic 1/X/2 option-set policy."""
from __future__ import annotations

from .calibration import validate_probabilities

OPTIONS = {"1", "X", "2", "1X", "X2", "12", "1X2"}


def decide(probabilities: dict[str, float], banko_allowed: bool, *, triple_gap: float = .05) -> dict[str, object]:
    probabilities = validate_probabilities(probabilities)
    ranked = sorted(probabilities, key=lambda key: probabilities[key], reverse=True)
    primary = ranked[0]
    reasons = [f"{primary} has highest ensemble probability"]
    if banko_allowed:
        selection = primary
        secondary = None
        reasons.append("banko permission is true")
    else:
        second, third = ranked[1], ranked[2]
        if probabilities[second] - probabilities[third] < triple_gap:
            selection = "1X2"
            primary = secondary = None
            reasons.append("banko permission is false and top-three outcomes are close")
        else:
            selection = "".join(sorted((primary, second), key=("1", "X", "2").index))
            secondary = second
            reasons.append("banko permission is false; top two outcomes selected")
    return {"selection": selection, "primary": primary, "secondary": secondary,
            "confidence": "high" if banko_allowed else "medium", "banko": banko_allowed, "reasons": reasons,
            "probabilities": probabilities}


__all__ = ["OPTIONS", "decide"]
