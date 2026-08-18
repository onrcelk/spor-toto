"""Hermes-facing high-level Sport Toto domain service."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .journal_finalizer import project_state, write_idempotent
from .orchestration import SportTotoWorkflow
from .tool_boundary import ResearchToolRegistry


@dataclass(frozen=True)
class WorkflowResult:
    run_id: str
    status: str
    fixture_count: int
    completed_stages: tuple[str, ...]
    summary: dict[str, Any]
    artifacts: dict[str, str]
    failed_stage: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SportTotoService:
    """Single domain entry point; internal adapters remain hidden from callers."""

    def __init__(self, tools: ResearchToolRegistry) -> None:
        self.tools = tools

    def run(self, *, run_id: str, fixtures: list[dict[str, Any]], prediction_artifact: str,
            journal_path: str, actual: dict[str, str] | None = None) -> WorkflowResult:
        workflow = SportTotoWorkflow(run_id, fixtures, self.tools)
        state = workflow.initial_state
        artifacts = {"journal": journal_path}
        current_stage = "fixture_validation"
        try:
            current_stage = "research_collection"
            state = workflow.run_research()
            current_stage = "prediction"
            state = workflow.run_prediction(state, prediction_artifact)
            current_stage = "calibration"
            state = workflow.run_calibration(state)
            current_stage = "ensemble"
            state = workflow.run_ensemble(state)
            current_stage = "risk"
            state = workflow.run_risk(state)
            current_stage = "decision"
            state = workflow.run_decision(state)
            current_stage = "journal"
            records = project_state(state)
            write_idempotent(journal_path, records)
            state = state.advance("journal")
            state = workflow.run_coupon(state, actual=actual)
            summary = {
                "high_risk_matches": sum(row["risk_level"] == "high" for row in state.risk),
                "banko_count": sum(row["banko"] for row in state.decisions),
                "double_count": sum(len(row["selection"]) == 2 for row in state.decisions),
                "triple_count": sum(row["selection"] == "1X2" for row in state.decisions),
                "scenarios": state.coupon["scenario_count"], "filtered_scenarios": state.coupon["filtered_scenario_count"],
            }
            return WorkflowResult(run_id, "completed", len(fixtures), (*state.stage_history,), summary, artifacts)
        except Exception as exc:
            return WorkflowResult(run_id, "failed", len(fixtures), (*state.stage_history,), {}, artifacts, current_stage, str(exc))


def load_fixture_file(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{"match_id": f"M{int(row['match_index']):02d}", "home": row["home_team"], "away": row["away_team"], "data_quality": {"score": .95}} for row in payload["matches"]]


__all__ = ["SportTotoService", "WorkflowResult", "load_fixture_file"]
