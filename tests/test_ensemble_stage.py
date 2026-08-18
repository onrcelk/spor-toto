import pytest

from sportoto.calibration import IdentityCalibrator
from sportoto.orchestration import SportTotoWorkflow, ensemble_stage
from sportoto.orchestration.state import WorkflowState
from sportoto.tool_boundary import ResearchToolRegistry
from sportoto.adapter_contracts import AdapterRegistry

ARTIFACT = "data/predictions/2026-08-21-predictions_HYBRID_TRANSFER_COUNTS.json"


def prepared_state():
    fixtures = [{"match_id": f"M{i:02d}", "home": f"Home {i}", "away": f"Away {i}"} for i in range(1, 16)]
    workflow = SportTotoWorkflow("2026W34", fixtures, ResearchToolRegistry(AdapterRegistry()))
    state = workflow.run_prediction(workflow.initial_state, ARTIFACT)
    return workflow.run_calibration(state, IdentityCalibrator())


def test_ensemble_uses_calibrated_predictions_for_15_matches():
    state = ensemble_stage(prepared_state())
    assert len(state.ensemble) == 15
    assert state.ensemble_metadata["input"] == "calibrated_predictions"
    for row in state.ensemble:
        assert set(row["output"]) == {"1", "X", "2"}
        assert sum(row["output"].values()) == pytest.approx(1.0)


def test_ensemble_requires_calibration():
    raw = WorkflowState("run", model_predictions=({"match_id": "M01", "model": {"1": .6, "X": .2, "2": .2}, "features": {"home_xg_avg": 1, "away_xg_avg": 1}},))
    with pytest.raises(ValueError, match="calibrated_predictions"):
        ensemble_stage(raw)


def test_ensemble_missing_xg_fails_without_fallback():
    state = prepared_state()
    broken = state.model_predictions[0].copy()
    broken["features"] = {}
    broken_state = state.advance("test_break", model_predictions=(broken, *state.model_predictions[1:]))
    with pytest.raises(ValueError, match="missing xg"):
        ensemble_stage(broken_state)


def test_ensemble_stage_cannot_run_twice():
    state = ensemble_stage(prepared_state())
    with pytest.raises(ValueError, match="already applied"):
        ensemble_stage(state)
