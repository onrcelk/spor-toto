from sportoto.adapter_contracts import AdapterRegistry
from sportoto.squad_adapter import SquadAdapter
from sportoto.squad_providers import StaticSquadProvider


def adapter(rows):
    return SquadAdapter(StaticSquadProvider(rows, source="official"))


def test_confirmed_unavailable_claim_becomes_verified_evidence():
    result = adapter([{"match_id": "M04", "claims": [{"type": "injury", "player": "Player X", "status": "unavailable", "freshness": "fresh", "verified": True, "source_score": .96}]}]).retrieve("M04", {})
    assert result.status == "success"
    assert result.evidence[0].verified is True
    assert result.evidence[0].details["status"] == "unavailable"


def test_uncertain_claim_is_not_fabricated_as_verified():
    result = adapter([{"match_id": "M04", "claims": [{"type": "player_availability", "player": "Player X", "status": "uncertain", "freshness": "unknown", "verified": False}]}]).retrieve("M04", {})
    assert result.status == "success"
    assert result.evidence[0].verified is False


def test_invalid_claim_is_dropped_without_fabrication():
    result = adapter([{"match_id": "M04", "claims": [{"type": "goal", "player": "Player X", "status": "unavailable"}]}]).retrieve("M04", {})
    assert result.status == "success"
    assert result.evidence == ()


def test_missing_squad_is_retrieval_failure_without_evidence():
    result = adapter([]).retrieve("M04", {})
    assert result.status == "unavailable"
    assert result.evidence == ()


def test_registry_calls_only_requested_squad_adapter():
    registry = AdapterRegistry()
    registry.register(adapter([]))
    result = registry.retrieve(["squad"], "M04")
    assert result[0].category == "squad"
    assert result[0].status == "unavailable"
