"""Rule-based risk policy; it never changes prediction probabilities."""
from __future__ import annotations

from typing import Any

from .calibration import validate_probabilities


def _level(flags: set[str], data_quality: float, disagreement: float) -> str:
    critical = {"source_conflict", "research_exhausted", "critical_squad_uncertainty"}
    if flags & critical:
        return "high"
    if "missing_market_odds" in flags or "squad_uncertainty" in flags or data_quality < .85 or disagreement > .15:
        return "medium"
    return "low"


def assess_risk(*, data_quality: float, source_conflict: bool = False,
                squad_uncertainty: bool = False, market_available: bool = True,
                cold_start: bool = False, research_exhausted: bool = False,
                model_disagreement: float = 0.0) -> dict[str, Any]:
    flags: set[str] = set()
    if source_conflict: flags.add("source_conflict")
    if squad_uncertainty: flags.add("squad_uncertainty")
    if not market_available: flags.add("missing_market_odds")
    if cold_start: flags.add("cold_start")
    if research_exhausted: flags.add("research_exhausted")
    if model_disagreement > .15: flags.add("high_model_disagreement")
    level = _level(flags, float(data_quality), float(model_disagreement))
    critical = bool(flags & {"source_conflict", "research_exhausted", "critical_squad_uncertainty"})
    return {"risk_level": level, "confidence": {"low": "high", "medium": "medium", "high": "low"}[level],
            "risk_score": round(min(1.0, (len(flags) * .15) + max(0.0, .85 - float(data_quality)) + float(model_disagreement)), 4),
            "flags": sorted(flags), "factors": {"data_quality": float(data_quality), "source_conflict": source_conflict,
            "squad_uncertainty": squad_uncertainty, "market_available": market_available, "cold_start": cold_start,
            "research_exhausted": research_exhausted, "model_disagreement": float(model_disagreement)},
            "banko_allowed": level == "low" and not critical}


def model_disagreement(probability_sets: list[dict[str, float]]) -> float:
    if len(probability_sets) < 2:
        return 0.0
    validated = [validate_probabilities(values) for values in probability_sets]
    return max(max(row[key] for row in validated) - min(row[key] for row in validated) for key in ("1", "X", "2"))


__all__ = ["assess_risk", "model_disagreement"]
