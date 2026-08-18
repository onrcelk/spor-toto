from sportoto.research_orchestration import apply_research_to_journal, validate_evidence
from sportoto.squad_adapter import SquadAdapter
from sportoto.squad_providers import StaticSquadProvider


def test_conflicting_squad_sources_are_not_majority_resolved():
    a = SquadAdapter(StaticSquadProvider([{"match_id": "M04", "claims": [
        {"type": "player_availability", "player": "Player X", "status": "available", "freshness": "fresh", "verified": True, "source_score": .96}
    ]}], source="official"))
    b = SquadAdapter(StaticSquadProvider([{"match_id": "M04", "claims": [
        {"type": "player_availability", "player": "Player X", "status": "unavailable", "freshness": "fresh", "verified": True, "source_score": .82}
    ]}], source="news"))
    evidence = list(a.retrieve("M04", {}).evidence) + list(b.retrieve("M04", {}).evidence)
    assert validate_evidence(evidence)["agreement"] == "conflicted"
    updated = apply_research_to_journal({"risk": {"flags": [], "banko_allowed": True}, "source_reliability": {}}, evidence)
    assert updated["risk"]["banko_allowed"] is False
    assert "squad_source_conflict" in updated["risk"]["flags"]
