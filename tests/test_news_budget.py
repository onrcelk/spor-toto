from sportoto.adapter_contracts import AdapterRegistry
from sportoto.news_adapter import NewsAdapter
from sportoto.news_providers import StaticNewsProvider


def test_news_category_is_only_called_when_requested():
    registry = AdapterRegistry()
    registry.register(NewsAdapter(StaticNewsProvider([])))
    result = registry.retrieve(["news"], "M04", {"max_attempts": {"news": 1}})[0]
    assert result.category == "news"
    assert result.status == "unavailable"


def test_research_budget_exhaustion_is_not_evidence():
    registry = AdapterRegistry()
    registry.register(NewsAdapter(StaticNewsProvider([])))
    result = registry.retrieve(["news"], "M04", {"attempts": {"news": 1}, "max_attempts": {"news": 1}})[0]
    assert result.error == "research_exhausted"
    assert result.evidence == ()
