from types import SimpleNamespace

from sportoto.adapter_contracts import AdapterRegistry, RetrievalResult
from sportoto.tool_boundary import ResearchToolRegistry, ToolSpec, tools_from_research_decision


class FakeAdapter:
    def __init__(self, category):
        self.category = category
    def retrieve(self, match_id, context):
        return RetrievalResult(self.category, match_id, "success")


def test_only_allowed_categories_reach_adapter_registry():
    adapters = AdapterRegistry()
    adapters.register(FakeAdapter("odds"))
    adapters.register(FakeAdapter("news"))
    tools = ResearchToolRegistry(adapters)
    tools.register(ToolSpec("odds_lookup", "odds", max_attempts=1))
    result = tools.run(["odds", "news"], "M04")
    assert [r.status for r in result] == ["success", "unavailable"]
    assert result[1].error == "tool_not_allowed"


def test_research_decision_controls_tool_calls():
    adapters = AdapterRegistry()
    adapters.register(FakeAdapter("squad"))
    tools = ResearchToolRegistry(adapters)
    tools.register(ToolSpec("squad_lookup", "squad", max_attempts=2))
    decision = SimpleNamespace(research_required=True, categories=("squad",))
    assert tools_from_research_decision(tools, decision, "M04")[0].status == "success"


def test_no_research_means_no_tool_call():
    tools = ResearchToolRegistry(AdapterRegistry())
    decision = SimpleNamespace(research_required=False, categories=())
    assert tools_from_research_decision(tools, decision, "M04") == []


def test_tool_budget_is_enforced_at_boundary():
    adapters = AdapterRegistry()
    adapters.register(FakeAdapter("news"))
    tools = ResearchToolRegistry(adapters)
    tools.register(ToolSpec("news_lookup", "news", max_attempts=1))
    result = tools.run(["news"], "M04", attempts={"news": 1})
    assert result[0].error == "research_exhausted"
