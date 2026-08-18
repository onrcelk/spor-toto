import pytest

from sportoto.adapter_contracts import AdapterRegistry
from sportoto.orchestration import SportTotoWorkflow, WorkflowState
from sportoto.tool_boundary import ResearchToolRegistry, ToolSpec


def test_state_advance_is_immutable_and_tracks_stages():
    state = WorkflowState("run", fixtures=({"match_id": "M01", "home": "A", "away": "B"},))
    next_state = state.advance("fixture_validation", audit={"fixture_count": 1})
    assert state.stage_history == ()
    assert next_state.stage_history == ("fixture_validation",)
    with pytest.raises(ValueError):
        next_state.advance("fixture_validation")


def test_workflow_research_uses_only_decided_categories():
    tools = ResearchToolRegistry(AdapterRegistry())
    tools.register(ToolSpec("odds_lookup", "odds"))
    fixtures = [{"match_id": "M01", "home": "A", "away": "B", "data_quality": {"score": .5, "missing_fields": ["market_odds"]}}]
    state = SportTotoWorkflow("run", fixtures, tools).run_until_research()
    assert state.stage_history == ("fixture_validation", "research_decision", "research_collection")
    assert state.research_decisions[0]["categories"] == ("odds",)
    assert state.retrievals[0]["error"] == "adapter_not_registered"


def test_complete_data_does_not_call_tools():
    tools = ResearchToolRegistry(AdapterRegistry())
    fixtures = [{"match_id": "M01", "home": "A", "away": "B", "data_quality": {"score": .95}}]
    state = SportTotoWorkflow("run", fixtures, tools).run_until_research()
    assert state.research_decisions[0]["research_required"] is False
    assert state.retrievals == ()


def test_fixture_validation_rejects_duplicate_ids():
    tools = ResearchToolRegistry(AdapterRegistry())
    fixtures = [{"match_id": "M01", "home": "A", "away": "B"}, {"match_id": "M01", "home": "C", "away": "D"}]
    with pytest.raises(ValueError):
        SportTotoWorkflow("run", fixtures, tools).run_until_research()


def test_full_15_match_workflow_reaches_research_collection():
    tools = ResearchToolRegistry(AdapterRegistry())
    fixtures = [{"match_id": f"M{i:02d}", "home": f"Home {i}", "away": f"Away {i}", "data_quality": {"score": .95}} for i in range(1, 16)]
    state = SportTotoWorkflow("2026W34", fixtures, tools).run_until_research()
    assert len(state.fixtures) == 15
    assert len(state.research_decisions) == 15
    assert state.stage_history[-1] == "research_collection"
