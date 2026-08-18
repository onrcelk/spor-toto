import pytest

from sportoto.orchestration import SportTotoWorkflow
from sportoto.tool_boundary import ResearchToolRegistry
from sportoto.adapter_contracts import AdapterRegistry


ARTIFACT = "data/predictions/2026-08-21-predictions_HYBRID_TRANSFER_COUNTS.json"


def test_prediction_stage_loads_existing_15_match_artifact():
    fixtures = [{"match_id": f"M{i:02d}", "home": f"Home {i}", "away": f"Away {i}"} for i in range(1, 16)]
    workflow = SportTotoWorkflow("2026W34", fixtures, ResearchToolRegistry(AdapterRegistry()))
    state = workflow.run_prediction(workflow.initial_state, ARTIFACT)
    assert len(state.model_predictions) == 15
    assert set(state.model_predictions[0]["model"]) == {"1", "X", "2"}
    assert "prediction" in state.stage_history


def test_prediction_stage_rejects_missing_match(tmp_path):
    artifact = tmp_path / "predictions.json"
    artifact.write_text('{"predictions": [{"match_id": "M01", "pred_home_win": 0.5, "pred_draw": 0.3, "pred_away_win": 0.2}]}')
    fixtures = [{"match_id": "M01", "home": "A", "away": "B"}, {"match_id": "M02", "home": "C", "away": "D"}]
    workflow = SportTotoWorkflow("run", fixtures, ResearchToolRegistry(AdapterRegistry()))
    with pytest.raises(ValueError, match="missing matches"):
        workflow.run_prediction(workflow.initial_state, str(artifact))
