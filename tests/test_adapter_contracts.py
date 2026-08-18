from sportoto.adapter_contracts import AdapterRegistry, RetrievalResult, retrieval_failure
from sportoto.research_orchestration import Evidence, apply_research_to_journal, validate_evidence


def test_failed_retrieval_is_not_evidence():
    result = retrieval_failure("squad", "M04", "timeout", "provider timeout")
    assert result.evidence == ()
    assert result.status == "timeout"


def test_registry_only_calls_requested_registered_categories():
    class Odds:
        category = "odds"
        def retrieve(self, match_id, context):
            return RetrievalResult("odds", match_id, "success")
    registry = AdapterRegistry()
    registry.register(Odds())
    results = registry.retrieve(["odds", "squad"], "M04")
    assert [r.status for r in results] == ["success", "unavailable"]
    assert results[1].error == "adapter_not_registered"


def test_conflicting_fresh_evidence_blocks_banko():
    evidence = [
        Evidence.create("M04", "available", "squad", "official", source_reliability=.96, freshness="fresh", verified=True),
        Evidence.create("M04", "unavailable", "squad", "news", source_reliability=.82, freshness="fresh", verified=True),
    ]
    assert validate_evidence(evidence)["agreement"] == "conflicted"
    updated = apply_research_to_journal({"risk": {"flags": [], "banko_allowed": True}, "source_reliability": {}}, evidence)
    assert updated["risk"]["banko_allowed"] is False
    assert "squad_source_conflict" in updated["risk"]["flags"]
