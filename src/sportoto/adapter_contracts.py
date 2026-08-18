"""Provider-neutral adapter contracts for research orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from .research_orchestration import Evidence

RETRIEVAL_STATUSES = {"success", "timeout", "unavailable", "parse_error", "rate_limited"}
CATEGORIES = {"odds", "squad", "news"}


@dataclass(frozen=True)
class RetrievalResult:
    category: str
    match_id: str
    status: str
    evidence: tuple[Evidence, ...] = ()
    error: str | None = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"unsupported adapter category: {self.category}")
        if self.status not in RETRIEVAL_STATUSES:
            raise ValueError(f"unsupported retrieval status: {self.status}")
        if self.status == "success" and self.error:
            raise ValueError("successful retrieval cannot contain an error")
        if self.status != "success" and self.evidence:
            raise ValueError("failed retrieval must not be stored as evidence")


class ResearchAdapter(Protocol):
    category: str

    def retrieve(self, match_id: str, context: dict[str, Any]) -> RetrievalResult:
        ...


class AdapterRegistry:
    """Allowlisted adapter registry; no category means no tool call."""

    def __init__(self) -> None:
        self._adapters: dict[str, ResearchAdapter] = {}

    def register(self, adapter: ResearchAdapter) -> None:
        if adapter.category not in CATEGORIES:
            raise ValueError(f"unsupported adapter category: {adapter.category}")
        self._adapters[adapter.category] = adapter

    def retrieve(self, categories: list[str] | tuple[str, ...], match_id: str,
                 context: dict[str, Any] | None = None) -> list[RetrievalResult]:
        context = context or {}
        results = []
        for category in categories:
            attempts = int(context.get("attempts", {}).get(category, 0))
            max_attempts = int(context.get("max_attempts", {}).get(category, 1))
            if attempts >= max_attempts:
                results.append(RetrievalResult(category, match_id, "unavailable", error="research_exhausted"))
                continue
            adapter = self._adapters.get(category)
            if adapter is None:
                results.append(RetrievalResult(category, match_id, "unavailable", error="adapter_not_registered"))
                continue
            results.append(adapter.retrieve(match_id, context))
        return results


def retrieval_failure(category: str, match_id: str, status: str, error: str) -> RetrievalResult:
    return RetrievalResult(category=category, match_id=match_id, status=status, error=error)


__all__ = ["AdapterRegistry", "CATEGORIES", "RETRIEVAL_STATUSES", "ResearchAdapter", "RetrievalResult", "retrieval_failure"]
