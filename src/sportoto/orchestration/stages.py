"""Pure orchestration stages; domain workflow does not alter model internals."""
from __future__ import annotations

from typing import Any

from ..research_orchestration import decide_research
from ..tool_boundary import ResearchToolRegistry
from .state import WorkflowState


def validate_fixtures(state: WorkflowState) -> WorkflowState:
    if not state.fixtures:
        raise ValueError("workflow requires at least one fixture")
    seen = set()
    for fixture in state.fixtures:
        match_id = str(fixture.get("match_id", ""))
        if not match_id or match_id in seen or not fixture.get("home") or not fixture.get("away"):
            raise ValueError("fixtures must have unique match_id, home and away")
        seen.add(match_id)
    return state.advance("fixture_validation", audit={**state.audit, "fixture_count": len(state.fixtures)})


def decide_research_stage(state: WorkflowState) -> WorkflowState:
    decisions = []
    for fixture in state.fixtures:
        quality = fixture.get("data_quality", {})
        decision = decide_research(
            data_quality_score=float(quality.get("score", 0.0)),
            missing_fields=quality.get("missing_fields", []),
            stale_sources=quality.get("stale_sources", []),
            source_conflicts=quality.get("source_conflicts", []),
        )
        decisions.append({"match_id": fixture["match_id"], **decision.to_dict()})
    return state.advance("research_decision", research_decisions=tuple(decisions))


def collect_research(state: WorkflowState, tools: ResearchToolRegistry, attempts: dict[str, int] | None = None) -> WorkflowState:
    retrievals = []
    evidence = []
    for decision in state.research_decisions:
        results = tools.run(decision["categories"], decision["match_id"], attempts)
        for result in results:
            retrievals.append({"match_id": result.match_id, "category": result.category, "status": result.status, "error": result.error})
            evidence.extend(item.to_dict() for item in result.evidence)
    return state.advance("research_collection", retrievals=tuple(retrievals), evidence=tuple(evidence))


def mark_stage(state: WorkflowState, stage: str) -> WorkflowState:
    """Explicit placeholder for later deterministic model stages; does not invent output."""
    return state.advance(stage)


__all__ = ["collect_research", "decide_research_stage", "mark_stage", "validate_fixtures"]
