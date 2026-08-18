"""Tool-calling boundary between research decisions and adapter registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapter_contracts import AdapterRegistry, RetrievalResult


@dataclass(frozen=True)
class ToolSpec:
    name: str
    category: str
    enabled: bool = True
    max_attempts: int = 1


class ResearchToolRegistry:
    """Allowlisted tool facade; callers request categories, never adapters."""

    def __init__(self, adapter_registry: AdapterRegistry) -> None:
        self.adapters = adapter_registry
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not spec.enabled:
            return
        if spec.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._tools[spec.category] = spec

    def allowed_categories(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def run(self, categories: list[str] | tuple[str, ...], match_id: str,
            attempts: dict[str, int] | None = None) -> list[RetrievalResult]:
        attempts = attempts or {}
        selected: list[str] = []
        denied: dict[str, RetrievalResult] = {}
        for category in categories:
            spec = self._tools.get(category)
            if spec is None:
                denied[category] = RetrievalResult(category, match_id, "unavailable", error="tool_not_allowed")
            else:
                selected.append(category)
        context = {
            "attempts": attempts,
            "max_attempts": {category: self._tools[category].max_attempts for category in selected},
        }
        allowed_results = {result.category: result for result in self.adapters.retrieve(selected, match_id, context)}
        return [denied.get(category) or allowed_results[category] for category in categories]


def tools_from_research_decision(tool_registry: ResearchToolRegistry, decision: Any,
                                 match_id: str, attempts: dict[str, int] | None = None) -> list[RetrievalResult]:
    """Execute only categories explicitly returned by ResearchDecision."""
    if not decision.research_required:
        return []
    return tool_registry.run(list(decision.categories), match_id, attempts)


__all__ = ["ResearchToolRegistry", "ToolSpec", "tools_from_research_decision"]
