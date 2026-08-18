from sportoto.adapter_contracts import AdapterRegistry
from sportoto.news_adapter import NewsAdapter
from sportoto.news_providers import StaticNewsProvider
from sportoto.research_orchestration import apply_research_to_journal


def test_fresh_verified_news_claim_becomes_evidence():
    result = NewsAdapter(StaticNewsProvider([{"match_id": "M04", "claims": [{"type": "rotation", "value": "rotation_possible", "subject": "home", "freshness": "fresh", "verified": True, "source_score": .80}]}], "official_news")).retrieve("M04", {})
    assert result.status == "success"
    assert result.evidence[0].verified is True
    assert result.evidence[0].details["type"] == "rotation"


def test_invalid_news_claim_is_not_fabricated():
    result = NewsAdapter(StaticNewsProvider([{"match_id": "M04", "claims": [{"type": "prediction", "value": "home_win"}]}])).retrieve("M04", {})
    assert result.evidence == ()


def test_missing_news_is_retrieval_failure():
    result = NewsAdapter(StaticNewsProvider([])).retrieve("M04", {})
    assert result.status == "unavailable"
    assert result.evidence == ()


def test_unverified_news_blocks_banko():
    evidence = list(NewsAdapter(StaticNewsProvider([{"match_id": "M04", "claims": [{"type": "coach_change", "value": "changed", "freshness": "unknown", "verified": False}]}])).retrieve("M04", {}).evidence)
    updated = apply_research_to_journal({"risk": {"flags": [], "banko_allowed": True}, "source_reliability": {}}, evidence)
    assert updated["risk"]["banko_allowed"] is False
    assert "news_evidence_unconfirmed" in updated["risk"]["flags"]
