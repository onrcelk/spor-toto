from sportoto.research_orchestration import (
    Evidence,
    apply_research_to_journal,
    decide_research,
    validate_evidence,
)


def test_missing_odds_and_lineup_trigger_research():
    decision = decide_research(data_quality_score=.6, missing_fields=["market_odds", "lineup"])
    assert decision.research_required is True
    assert decision.priority == "high"
    assert set(decision.categories) == {"odds", "squad"}


def test_complete_fresh_data_stops_research():
    decision = decide_research(data_quality_score=.94)
    assert decision.research_required is False
    assert decision.priority == "none"


def test_two_fresh_verified_sources_confirm_claim():
    evidence = [
        Evidence.create("M04", "striker unavailable", "squad", "official", source_reliability=.96, freshness="fresh", verified=True),
        Evidence.create("M04", "striker unavailable", "squad", "reliable_news", source_reliability=.82, freshness="fresh", verified=True),
    ]
    result = validate_evidence(evidence)
    assert result["verified"] is True
    assert result["agreement"] == "confirmed"


def test_unconfirmed_evidence_blocks_banko():
    record = {"risk": {"flags": [], "banko_allowed": True}, "source_reliability": {}}
    evidence = [Evidence.create("M04", "lineup uncertain", "squad", "youtube", freshness="unknown", verified=False)]
    updated = apply_research_to_journal(record, evidence)
    assert updated["risk"]["banko_allowed"] is False
    assert "squad_evidence_unconfirmed" in updated["risk"]["flags"]
