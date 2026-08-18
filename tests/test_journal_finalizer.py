import json

import pytest

from sportoto.journal_finalizer import project_state, write_idempotent
from sportoto.orchestration.state import WorkflowState


def full_state(n=15):
    ids = [f"M{i:02d}" for i in range(1, n + 1)]
    fixtures = tuple({"match_id": mid, "home": "A", "away": "B"} for mid in ids)
    model = tuple({"match_id": mid, "model": {"1": .6, "X": .25, "2": .15}} for mid in ids)
    calibrated = tuple({"match_id": mid, "raw": {"1": .6, "X": .25, "2": .15}, "calibrated": {"1": .6, "X": .25, "2": .15}} for mid in ids)
    ensemble = tuple({"match_id": mid, "output": {"1": .6, "X": .25, "2": .15}} for mid in ids)
    risk = tuple({"match_id": mid, "risk_level": "low", "confidence": "high", "risk_score": 0, "flags": [], "banko_allowed": True} for mid in ids)
    decisions = tuple({"match_id": mid, "selection": "1", "primary": "1", "secondary": None, "confidence": "high", "banko": True, "reasons": ["test"]} for mid in ids)
    return WorkflowState("2026W34", fixtures=fixtures, model_predictions=model, calibrated_predictions=calibrated,
                         ensemble=ensemble, risk=risk, decisions=decisions,
                         stage_history=("fixture_validation", "research_decision", "research_collection", "prediction", "calibration", "ensemble", "risk", "decision"))


def test_project_state_creates_15_complete_audit_records():
    records = project_state(full_state())
    assert len(records) == 15
    assert records[0]["record_id"] == "2026W34:M01:v1"
    assert records[0]["prediction"]["raw"] == records[0]["prediction"]["calibrated"]
    assert records[0]["post_match"]["actual"] is None
    assert "decision" in records[0] and "stages_completed" in records[0]["research"]


def test_projection_fails_if_one_stage_lacks_a_match():
    state = full_state()
    broken = state.__class__(**{**state.snapshot(), "decisions": state.decisions[:-1]})
    with pytest.raises(ValueError, match="exact fixture coverage"):
        project_state(broken)


def test_idempotent_writer_has_no_duplicates(tmp_path):
    path = tmp_path / "journal.jsonl"
    records = project_state(full_state())
    write_idempotent(path, records + records)
    lines = path.read_text().splitlines()
    assert len(lines) == 15
    assert len({json.loads(line)["record_id"] for line in lines}) == 15
