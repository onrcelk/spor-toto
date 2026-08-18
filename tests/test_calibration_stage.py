import pytest

from sportoto.calibration import IdentityCalibrator
from sportoto.orchestration import SportTotoWorkflow, WorkflowState, calibration_stage
from sportoto.tool_boundary import ResearchToolRegistry
from sportoto.adapter_contracts import AdapterRegistry


def state_with_predictions():
    return WorkflowState("run", model_predictions=tuple({"match_id": f"M{i:02d}", "model": {"1": .6, "X": .25, "2": .15}} for i in range(1, 16)))


def test_identity_calibration_produces_15_rows_and_metadata():
    state = calibration_stage(state_with_predictions(), IdentityCalibrator(version="identity-test"))
    assert len(state.calibrated_predictions) == 15
    assert state.calibration_metadata["method"] == "identity"
    assert state.calibration_metadata["version"] == "identity-test"
    for row in state.calibrated_predictions:
        assert set(row["calibrated"]) == {"1", "X", "2"}
        assert sum(row["calibrated"].values()) == pytest.approx(1.0)
        assert all(0 <= p <= 1 for p in row["calibrated"].values())


def test_calibration_preserves_input_state():
    original = state_with_predictions()
    calibration_stage(original)
    assert original.calibrated_predictions == ()
    assert original.stage_history == ()


def test_calibration_requires_predictions():
    with pytest.raises(ValueError, match="model_predictions"):
        calibration_stage(WorkflowState("run"))


def test_calibration_stage_cannot_run_twice():
    state = calibration_stage(state_with_predictions())
    with pytest.raises(ValueError, match="already applied"):
        calibration_stage(state)


def test_workflow_calibration_uses_explicit_identity_fallback():
    workflow = SportTotoWorkflow("run", [], ResearchToolRegistry(AdapterRegistry()))
    state = workflow.run_calibration(state_with_predictions())
    assert state.calibration_metadata["method"] == "identity"
