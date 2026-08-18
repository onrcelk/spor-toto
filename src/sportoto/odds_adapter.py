"""Provider-neutral odds adapter: raw 1/X/2 odds -> market evidence."""
from __future__ import annotations

import math
from typing import Any

from .adapter_contracts import RetrievalResult
from .odds_providers import OddsProvider, TelegramStaticOddsProvider
from .research_orchestration import Evidence


class OddsAdapter:
    category = "odds"

    def __init__(self, provider: OddsProvider) -> None:
        self.provider = provider

    def retrieve(self, match_id: str, context: dict[str, Any]) -> RetrievalResult:
        try:
            row = self.provider.fetch(match_id, context)
        except TimeoutError as exc:
            return RetrievalResult("odds", match_id, "timeout", error=str(exc))
        except Exception as exc:
            return RetrievalResult("odds", match_id, "unavailable", error=f"provider_error: {exc}")
        if row is None:
            return RetrievalResult("odds", match_id, "unavailable", error="odds_not_found")
        if row.get("provider_duplicate"):
            return RetrievalResult("odds", match_id, "parse_error", error="duplicate_odds_row")
        normalized = normalize_odds(row.get("odds", {}))
        freshness = str(row.get("freshness", context.get("freshness", "unknown")))
        verified = bool(normalized.get("market_available")) and freshness == "fresh"
        claim = "1/X/2 odds unavailable"
        if normalized.get("market_available"):
            o = normalized["odds"]
            claim = f"1={o['1']}; X={o['X']}; 2={o['2']}"
        evidence = Evidence.create(
            match_id, claim, "odds", str(row.get("source", self.provider.source)),
            source_url=row.get("source_url"),
            source_reliability=float(row.get("source_score", .70)),
            published_at=row.get("published_at"), freshness=freshness, verified=verified,
            details=normalized,
        )
        return RetrievalResult("odds", match_id, "success", evidence=(evidence,))


def normalize_odds(odds: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in ("1", "X", "2") if k not in odds or odds[k] in (None, "")]
    if missing:
        return {"market_available": False, "status": "incomplete_market_odds", "missing": missing}
    try:
        values = {k: float(odds[k]) for k in ("1", "X", "2")}
    except (TypeError, ValueError) as exc:
        return {"market_available": False, "status": "invalid_market_odds", "error": str(exc)}
    if any(not math.isfinite(v) or v <= 1.0 for v in values.values()):
        return {"market_available": False, "status": "invalid_market_odds", "error": "all odds must be finite and > 1"}
    raw = {k: 1.0 / v for k, v in values.items()}
    overround = sum(raw.values())
    return {"market_available": True, "status": "complete", "odds": values,
            "raw_implied": raw, "overround": overround,
            "normalized_probability": {k: v / overround for k, v in raw.items()}}


class StaticOddsAdapter(OddsAdapter):
    """Backward-compatible wrapper; prefer TelegramStaticOddsProvider + OddsAdapter."""

    def __init__(self, rows: list[dict[str, Any]], source: str = "static_odds") -> None:
        provider = TelegramStaticOddsProvider(rows)
        provider.source = source
        super().__init__(provider)


__all__ = ["OddsAdapter", "StaticOddsAdapter", "normalize_odds"]
