from sportoto.evidence import EvidenceRecord, evidence_packet


def test_evidence_packet_separates_facts_from_summary():
    fact = EvidenceRecord("M1", "form", "home_points", 8, "football-data.org", "2026-08-17T00:00:00Z", 0.9, "supports_home")
    packet = evidence_packet("M1", [fact], "Home form is stronger.")
    data = packet.to_dict()
    assert data["facts"][0]["source"] == "football-data.org"
    assert data["summary"] == "Home form is stronger."


def test_evidence_record_rejects_invalid_confidence():
    try:
        EvidenceRecord("M1", "xg", "value", 1.0, "source", "now", 1.5, "neutral")
    except ValueError:
        return
    raise AssertionError("invalid confidence should fail")
