"""Deterministic Sport Toto workflow facade for Hermes-facing orchestration."""
from __future__ import annotations

from typing import Any

from ..tool_boundary import ResearchToolRegistry
from .stages import calibration_stage, collect_research, decide_research_stage, ensemble_stage, mark_stage, prediction_stage, validate_fixtures
from .state import WorkflowState


class SportTotoWorkflow:
    def __init__(self, run_id: str, fixtures: list[dict[str, Any]], tools: ResearchToolRegistry) -> None:
        self.initial_state = WorkflowState(run_id=run_id, fixtures=tuple(fixtures))
        self.tools = tools

    def run_research(self, attempts: dict[str, int] | None = None) -> WorkflowState:
        state = validate_fixtures(self.initial_state)
        state = decide_research_stage(state)
        return collect_research(state, self.tools, attempts)

    def run_until_research(self, attempts: dict[str, int] | None = None) -> WorkflowState:
        return self.run_research(attempts)

    def run_prediction(self, state: WorkflowState, artifact_path: str) -> WorkflowState:
        return prediction_stage(state, artifact_path)

    def run_calibration(self, state: WorkflowState, calibrator=None) -> WorkflowState:
        return calibration_stage(state, calibrator)

    def run_ensemble(self, state: WorkflowState, **weights) -> WorkflowState:
        return ensemble_stage(state, **weights)

    @staticmethod
    def continue_stage(state: WorkflowState, stage: str) -> WorkflowState:
        allowed = {"prediction", "calibration", "ensemble", "risk", "decision_journal", "coupon"}
        if stage not in allowed:
            raise ValueError(f"unknown workflow stage: {stage}")
        return mark_stage(state, stage)


__all__ = ["SportTotoWorkflow"]
