import json

import pytest

from sportoto.decision_journal import (
    append_decision_record,
    build_decision_record,
    source_reliability,
    update_post_match,
)


def _record():
    return build_decision_record(
        "2026W34", "M04", {"home": "A", "away": "B"},
        {"gbm": {"prediction": "1", "probabilities": {"1": .6, "X": .2, "2": .2}}},
        {"1": .6, "X": .2, "2": .2}, {"1": .58, "X": .25, "2": .17},
        {"selection": "1X", "confidence": "medium", "reasons": ["model agreement"]},
        reliability={"odds": source_reliability("high", .94)},
    )


def test_decision_record_has_auditable_layers():
    r = _record()
    assert r["schema_version"] == "1.0"
    assert r["prediction"]["calibrated"]["1"] == .58
    assert r["post_match"]["actual"] is None


def test_append_jsonl_and_post_match_update(tmp_path):
    r = _record()
    path = tmp_path / "decision_journal.jsonl"
    append_decision_record(path, r)
    assert len(path.read_text().splitlines()) == 1
    assert update_post_match(r, "X")["post_match"]["hit"] is True
    assert update_post_match(r, "2", "wrong_direction")["post_match"]["hit"] is False


def test_invalid_source_score_rejected():
    with pytest.raises(ValueError):
        source_reliability("high", 1.2)
