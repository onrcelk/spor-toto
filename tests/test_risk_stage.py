import pytest

from sportoto.orchestration import SportTotoWorkflow, risk_stage
from sportoto.orchestration.state import WorkflowState
from sportoto.risk import assess_risk, model_disagreement
from sportoto.tool_boundary import ResearchToolRegistry
from sportoto.adapter_contracts import AdapterRegistry


def test_same_probability_can_have_low_or_high_risk():
    low = assess_risk(data_quality=.96, market_available=True)
    high = assess_risk(data_quality=.71, market_available=False, squad_uncertainty=True, source_conflict=True)
    assert low["risk_level"] == "low" and low["banko_allowed"] is True
    assert high["risk_level"] == "high" and high["banko_allowed"] is False


def test_probability_is_not_changed_by_risk_stage():
    ensemble = ({"match_id": "M01", "inputs": {"calibrated_model": {"1": .68, "X": .2, "2": .12}, "market": None}, "output": {"1": .68, "X": .2, "2": .12}},)
    state = WorkflowState("run", fixtures=({"match_id": "M01", "home": "A", "away": "B", "data_quality": {"score": .6, "cold_start": True}},), ensemble=ensemble)
    updated = risk_stage(state)
    assert updated.ensemble == state.ensemble
    assert updated.risk[0]["risk_level"] == "medium"


def test_conflict_and_exhaustion_are_high_risk():
    ensemble = ({"match_id": "M01", "inputs": {"calibrated_model": {"1": .6, "X": .25, "2": .15}, "market": None}, "output": {"1": .6, "X": .25, "2": .15}},)
    retrievals = ({"match_id": "M01", "category": "news", "status": "unavailable", "error": "research_exhausted"},)
    state = WorkflowState("run", fixtures=({"match_id": "M01", "home": "A", "away": "B", "data_quality": {"score": .95}},), ensemble=ensemble, retrievals=retrievals)
    updated = risk_stage(state)
    assert updated.risk[0]["risk_level"] == "high"
    assert updated.risk[0]["banko_allowed"] is False


def test_disagreement_thresholds():
    assert model_disagreement([{"1": .64, "X": .23, "2": .13}, {"1": .62, "X": .24, "2": .14}]) == pytest.approx(.02)


def test_risk_requires_ensemble():
    with pytest.raises(ValueError, match="ensemble"):
        risk_stage(WorkflowState("run"))


def test_risk_stage_handles_15_ensemble_rows():
    rows = tuple({"match_id": f"M{i:02d}", "inputs": {"calibrated_model": {"1": .6, "X": .25, "2": .15}, "market": None}, "output": {"1": .6, "X": .25, "2": .15}} for i in range(1, 16))
    fixtures = tuple({"match_id": f"M{i:02d}", "home": f"A{i}", "away": f"B{i}", "data_quality": {"score": .95}} for i in range(1, 16))
    updated = risk_stage(WorkflowState("run", fixtures=fixtures, ensemble=rows))
    assert len(updated.risk) == 15
    assert all(item["risk_level"] == "medium" for item in updated.risk)
