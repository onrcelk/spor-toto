import pytest

from sportoto.decision import decide
from sportoto.orchestration import decision_stage
from sportoto.orchestration.state import WorkflowState


def make_state(output, banko):
    return WorkflowState("run", ensemble=({"match_id": "M01", "output": output, "inputs": {}},), risk=({"match_id": "M01", "banko_allowed": banko},))


def test_banko_selects_highest_outcome():
    result = decide({"1": .68, "X": .2, "2": .12}, True)
    assert result["selection"] == "1"
    assert result["primary"] == "1"
    assert result["secondary"] is None


def test_non_banko_selects_top_two():
    result = decide({"1": .68, "X": .2, "2": .12}, False)
    assert result["selection"] == "1X"
    assert result["primary"] == "1"
    assert result["secondary"] == "X"
    assert result["banko"] is False


def test_close_top_three_produces_triple():
    result = decide({"1": .36, "X": .34, "2": .30}, False)
    assert result["selection"] == "1X2"
    assert result["primary"] is None
    assert result["secondary"] is None


def test_decision_requires_ensemble_and_risk():
    with pytest.raises(ValueError, match="ensemble and risk"):
        decision_stage(WorkflowState("run"))


def test_decision_does_not_change_ensemble_or_risk():
    state = make_state({"1": .68, "X": .2, "2": .12}, False)
    updated = decision_stage(state)
    assert updated.ensemble == state.ensemble
    assert updated.risk == state.risk
    assert updated.decisions[0]["selection"] == "1X"


def test_15_match_decisions_and_banko_invariant():
    ensemble = tuple({"match_id": f"M{i:02d}", "output": {"1": .6, "X": .25, "2": .15}, "inputs": {}} for i in range(1, 16))
    risk = tuple({"match_id": f"M{i:02d}", "banko_allowed": i % 2 == 0} for i in range(1, 16))
    state = decision_stage(WorkflowState("run", ensemble=ensemble, risk=risk))
    allowed = {"1", "X", "2", "1X", "X2", "12", "1X2"}
    assert len(state.decisions) == 15
    assert all(row["selection"] in allowed for row in state.decisions)
    assert all(row["selection"] not in {"1", "X", "2"} for row in state.decisions if not row["banko"])
