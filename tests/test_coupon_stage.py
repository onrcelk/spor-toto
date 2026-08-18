import pytest

from sportoto.h15 import apply_filters, build_coupon_state, generate_scenarios
from sportoto.orchestration import coupon_stage
from sportoto.orchestration.state import WorkflowState


def decisions():
    return tuple({"match_id": mid, "selection": selection} for mid, selection in [("M01", "1"), ("M02", "1X"), ("M03", "X2"), ("M04", "1"), ("M05", "12")])


def test_scenario_generator_count_is_product_of_option_sets():
    state = build_coupon_state(decisions())
    assert state["scenario_count"] == 8
    assert len(state["selected_scenarios"]) == 8


def test_filter_audit_and_actual_preservation():
    filters = [("remove_X_at_M02", lambda scenario: scenario["M02"] != "X")]
    actual = {"M01": "1", "M02": "X", "M03": "X", "M04": "1", "M05": "2"}
    state = build_coupon_state(decisions(), filters, actual)
    assert state["filters"][0]["before"] == 8
    assert state["filters"][0]["after"] == 4
    assert state["audit"]["actual_in_all_scenarios"] is True
    assert state["audit"]["actual_in_filtered"] is False
    assert state["audit"]["eliminated_by"] == "remove_X_at_M02"


def test_coupon_stage_does_not_change_decisions_or_predictions():
    workflow_state = WorkflowState("run", decisions=decisions(), ensemble=({"match_id": "M01"},))
    updated = coupon_stage(workflow_state)
    assert updated.decisions == workflow_state.decisions
    assert updated.ensemble == workflow_state.ensemble
    assert updated.coupon["scenario_count"] == 8


def test_coupon_requires_decisions():
    with pytest.raises(ValueError, match="decisions"):
        coupon_stage(WorkflowState("run"))


def test_empty_option_sets_rejected():
    with pytest.raises(ValueError):
        generate_scenarios({})


def test_15_match_coupon_state():
    decisions = tuple({"match_id": f"M{i:02d}", "selection": "1X" if i % 3 == 0 else "1"} for i in range(1, 16))
    state = build_coupon_state(decisions)
    assert len(state["option_sets"]) == 15
    assert state["scenario_count"] == 2 ** 5
    assert state["filtered_scenario_count"] == state["scenario_count"]
