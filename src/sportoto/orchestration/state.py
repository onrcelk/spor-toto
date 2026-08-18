"""Immutable state and stage contracts for the Sport Toto workflow."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class WorkflowState:
    run_id: str
    fixtures: tuple[dict[str, Any], ...] = ()
    research_decisions: tuple[dict[str, Any], ...] = ()
    retrievals: tuple[dict[str, Any], ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()
    data_quality: tuple[dict[str, Any], ...] = ()
    model_predictions: tuple[dict[str, Any], ...] = ()
    calibrated_predictions: tuple[dict[str, Any], ...] = ()
    calibration_metadata: Mapping[str, Any] = field(default_factory=dict)
    ensemble: tuple[dict[str, Any], ...] = ()
    risk: tuple[dict[str, Any], ...] = ()
    decisions: tuple[dict[str, Any], ...] = ()
    coupon: Mapping[str, Any] = field(default_factory=dict)
    audit: Mapping[str, Any] = field(default_factory=dict)
    stage_history: tuple[str, ...] = ()

    def advance(self, stage: str, **changes: Any) -> "WorkflowState":
        if stage in self.stage_history:
            raise ValueError(f"workflow stage already applied: {stage}")
        safe_changes = {key: deepcopy(value) for key, value in changes.items()}
        safe_changes["stage_history"] = (*self.stage_history, stage)
        return replace(self, **safe_changes)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy({key: getattr(self, key) for key in self.__dataclass_fields__})


Stage = Any

__all__ = ["Stage", "WorkflowState"]
