"""Provider-neutral squad adapter: availability claims -> evidence."""
from __future__ import annotations

from typing import Any

from .adapter_contracts import RetrievalResult
from .research_orchestration import Evidence
from .squad_providers import SquadProvider

CLAIM_TYPES = {"player_availability", "injury", "suspension", "expected_lineup", "goalkeeper_availability"}
STATUSES = {"available", "unavailable", "uncertain"}


class SquadAdapter:
    category = "squad"

    def __init__(self, provider: SquadProvider) -> None:
        self.provider = provider

    def retrieve(self, match_id: str, context: dict[str, Any]) -> RetrievalResult:
        try:
            claims = self.provider.fetch(match_id, context)
        except TimeoutError as exc:
            return RetrievalResult("squad", match_id, "timeout", error=str(exc))
        except Exception as exc:
            return RetrievalResult("squad", match_id, "unavailable", error=f"provider_error: {exc}")
        if claims is None:
            return RetrievalResult("squad", match_id, "unavailable", error="squad_not_found")
        evidence: list[Evidence] = []
        for claim in claims:
            normalized = self._normalize_claim(claim, match_id)
            if normalized is None:
                continue
            evidence.append(normalized)
        return RetrievalResult("squad", match_id, "success", evidence=tuple(evidence))

    def _normalize_claim(self, claim: dict[str, Any], match_id: str) -> Evidence | None:
        claim_type = str(claim.get("type", ""))
        status = str(claim.get("status", ""))
        player = str(claim.get("player", ""))
        if claim_type not in CLAIM_TYPES or status not in STATUSES or not player:
            return None
        freshness = str(claim.get("freshness", "unknown"))
        verified = bool(claim.get("verified", False)) and freshness == "fresh"
        statement = f"{player} {status} ({claim_type})"
        return Evidence.create(
            match_id, statement, "squad", str(claim.get("source", self.provider.source)),
            source_url=claim.get("source_url"), source_reliability=float(claim.get("source_score", .50)),
            published_at=claim.get("published_at"), freshness=freshness, verified=verified,
            details={"type": claim_type, "player": player, "status": status},
        )


__all__ = ["CLAIM_TYPES", "SquadAdapter"]
