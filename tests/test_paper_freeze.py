import json

import pytest

from sportoto.paper_testing import classify_evidence_coverage, freeze_daily_run


def fixtures(n=15):
    return [
        {"match_id": f"M{i:02d}", "home": f"Home {i}", "away": f"Away {i}",
         "data_quality": {"score": .6, "missing_fields": ["market_odds", "lineup"]}}
        for i in range(1, n + 1)
    ]


def test_evidence_coverage_distinguishes_not_required_from_missing_evidence():
    not_required = classify_evidence_coverage(False, (), {})
    assert not_required["coverage"] == "none"
    assert not_required["research_status"] == "not_required"
    assert not_required["required_categories"] == []
    assert classify_evidence_coverage(True, ("odds", "squad"), {})["coverage"] == "none"


def test_partial_and_confirmed_requirements_are_category_based():
    evidence = {
        "odds": [{"verified": True, "freshness": "fresh", "source": "a"},
                 {"verified": True, "freshness": "fresh", "source": "b"}],
        "squad": [{"verified": False, "freshness": "unknown", "source": "c"}],
    }
    partial = classify_evidence_coverage(True, ("odds", "squad"), evidence)
    assert partial["coverage"] == "partial"
    assert partial["category_coverage"]["odds"] == "confirmed"
    assert partial["category_coverage"]["squad"] == "none"

    evidence["squad"] = [
        {"verified": True, "freshness": "fresh", "source": "c"},
        {"verified": True, "freshness": "fresh", "source": "d"},
    ]
    assert classify_evidence_coverage(True, ("odds", "squad"), evidence)["coverage"] == "confirmed"


def test_freeze_daily_run_writes_immutable_manifest(tmp_path):
    path = tmp_path / "paper" / "runs" / "paper-2026-08-19.json"
    kwargs = dict(
        run_id="paper-2026-08-19", fixtures=fixtures(), manifest_path=path,
        prediction_artifact="data/predictions/p.json", model_version="HYBRID_TRANSFER_COUNTS:v1",
        ensemble_version="existing_ensemble:v1", calibration_version="identity-test",
        decision_policy_version="v1", h15_policy_version="v1",
        frozen_at="2026-08-19T10:00:00+00:00",
    )
    manifest = freeze_daily_run(**kwargs)
    assert manifest["fixture_count"] == 15
    assert manifest["status"] == "frozen_pre_match"
    assert manifest["model_version"] == "HYBRID_TRANSFER_COUNTS:v1"

    assert freeze_daily_run(**kwargs) == manifest
    with pytest.raises(ValueError, match="immutable"):
        freeze_daily_run(**{**kwargs, "model_version": "changed"})

    loaded = json.loads(path.read_text())
    assert loaded == manifest


def test_freeze_rejects_non_15_or_duplicate_fixtures(tmp_path):
    base = dict(
        run_id="paper-test", manifest_path=tmp_path / "run.json",
        prediction_artifact="p.json", model_version="m", ensemble_version="e",
        calibration_version="c", decision_policy_version="d", h15_policy_version="h",
    )
    with pytest.raises(ValueError, match="exactly 15"):
        freeze_daily_run(**base, fixtures=fixtures(14))
    duplicate = fixtures()
    duplicate[-1]["match_id"] = "M01"
    with pytest.raises(ValueError, match="unique"):
        freeze_daily_run(**base, fixtures=duplicate)
