"""Provider-neutral news adapter: normalized news claims -> evidence."""
from __future__ import annotations

from typing import Any

from .adapter_contracts import RetrievalResult
from .news_providers import NewsProvider
from .research_orchestration import Evidence

CLAIM_TYPES = {"lineup_intent", "injury_news", "suspension_news", "coach_change", "motivation_context", "rotation", "disciplinary_risk"}
CLAIM_VALUES = {"rotation_possible", "rotation_unlikely", "available", "unavailable", "uncertain", "changed", "stable", "positive", "negative"}


class NewsAdapter:
    category = "news"

    def __init__(self, provider: NewsProvider) -> None:
        self.provider = provider

    def retrieve(self, match_id: str, context: dict[str, Any]) -> RetrievalResult:
        try:
            claims = self.provider.fetch(match_id, context)
        except TimeoutError as exc:
            return RetrievalResult("news", match_id, "timeout", error=str(exc))
        except Exception as exc:
            return RetrievalResult("news", match_id, "unavailable", error=f"provider_error: {exc}")
        if claims is None:
            return RetrievalResult("news", match_id, "unavailable", error="news_not_found")
        evidence = []
        for claim in claims:
            item = self._normalize_claim(claim, match_id)
            if item is not None:
                evidence.append(item)
        return RetrievalResult("news", match_id, "success", evidence=tuple(evidence))

    def _normalize_claim(self, claim: dict[str, Any], match_id: str) -> Evidence | None:
        claim_type = str(claim.get("type", ""))
        value = str(claim.get("value", ""))
        subject = str(claim.get("subject", "team"))
        if claim_type not in CLAIM_TYPES or value not in CLAIM_VALUES:
            return None
        freshness = str(claim.get("freshness", "unknown"))
        verified = bool(claim.get("verified", False)) and freshness == "fresh"
        statement = f"{subject}: {claim_type}={value}"
        return Evidence.create(
            match_id, statement, "news", str(claim.get("source", self.provider.source)),
            source_url=claim.get("source_url"), source_reliability=float(claim.get("source_score", .40)),
            published_at=claim.get("published_at"), freshness=freshness, verified=verified,
            details={"type": claim_type, "value": value, "subject": subject},
        )


__all__ = ["CLAIM_TYPES", "NewsAdapter"]
