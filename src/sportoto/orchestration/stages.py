"""Pure orchestration stages; domain workflow does not alter model internals."""
from __future__ import annotations

from typing import Any

from ..calibration import Calibrator, IdentityCalibrator, validate_probabilities
from ..ensemble import ensemble_probabilities
from ..prediction import load_prediction_artifact
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


def prediction_stage(state: WorkflowState, artifact_path: str) -> WorkflowState:
    artifact = load_prediction_artifact(artifact_path)
    missing = [fixture["match_id"] for fixture in state.fixtures if fixture["match_id"] not in artifact]
    if missing:
        raise ValueError(f"prediction artifact missing matches: {missing}")
    predictions = tuple({"match_id": match_id, **artifact[match_id]} for match_id in (fixture["match_id"] for fixture in state.fixtures))
    return state.advance("prediction", model_predictions=predictions)


def calibration_stage(state: WorkflowState, calibrator: Calibrator | None = None) -> WorkflowState:
    if not state.model_predictions:
        raise ValueError("calibration requires model_predictions")
    active = calibrator or IdentityCalibrator()
    calibrated = []
    for prediction in state.model_predictions:
        raw = validate_probabilities(prediction["model"])
        calibrated.append({"match_id": prediction["match_id"], "raw": raw, "calibrated": active.transform(raw)})
    return state.advance("calibration", calibrated_predictions=tuple(calibrated), calibration_metadata=active.metadata)


def ensemble_stage(state: WorkflowState, *, model_weight: float = .55, market_weight: float = .30, dixon_weight: float = .15) -> WorkflowState:
    if not state.calibrated_predictions:
        raise ValueError("ensemble requires calibrated_predictions")
    results = []
    for calibrated in state.calibrated_predictions:
        if "calibrated" not in calibrated:
            raise ValueError(f"missing calibrated signal for {calibrated.get('match_id')}")
        source = next((row for row in state.model_predictions if row["match_id"] == calibrated["match_id"]), None)
        if source is None:
            raise ValueError(f"prediction match missing for {calibrated['match_id']}")
        features = source.get("features", {})
        home_xg = features.get("home_xg_avg")
        away_xg = features.get("away_xg_avg")
        if home_xg is None or away_xg is None:
            raise ValueError(f"missing xg features for {calibrated['match_id']}")
        market = source.get("market")
        output = ensemble_probabilities(calibrated["calibrated"], float(home_xg), float(away_xg), market, model_weight, market_weight, dixon_weight)
        results.append({"match_id": calibrated["match_id"], "inputs": {"calibrated_model": calibrated["calibrated"], "market": market, "home_xg": home_xg, "away_xg": away_xg}, "output": output})
    metadata = {"method": "existing_ensemble", "weights": {"model": model_weight, "market": market_weight, "dixon": dixon_weight}, "input": "calibrated_predictions", "output": "ensemble"}
    return state.advance("ensemble", ensemble=tuple(results), ensemble_metadata=metadata)


def mark_stage(state: WorkflowState, stage: str) -> WorkflowState:
    """Explicit placeholder for later deterministic model stages; does not invent output."""
    return state.advance(stage)


__all__ = ["calibration_stage", "collect_research", "decide_research_stage", "ensemble_stage", "mark_stage", "prediction_stage", "validate_fixtures"]
