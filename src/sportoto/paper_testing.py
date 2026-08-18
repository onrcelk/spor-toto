"""Frozen daily paper-test runs and evidence coverage classification."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .research_orchestration import decide_research

COVERAGE_LEVELS = {"none", "partial", "confirmed"}


def _category_is_confirmed(items: Iterable[Mapping[str, Any]]) -> bool:
    reliable = [
        item for item in items
        if bool(item.get("verified")) and item.get("freshness") == "fresh"
    ]
    # Match the existing evidence contract: confirmation requires two fresh,
    # verified observations from distinct sources.
    return len({str(item.get("source", "")) for item in reliable}) >= 2


def classify_evidence_coverage(
    research_required: bool,
    required_categories: Iterable[str],
    evidence_by_category: Mapping[str, Iterable[Mapping[str, Any]]],
) -> dict[str, Any]:
    categories = sorted({str(category) for category in required_categories})
    category_coverage = {
        category: ("confirmed" if _category_is_confirmed(evidence_by_category.get(category, ())) else "none")
        for category in categories
    }
    if not categories:
        coverage = "none"
    elif all(value == "confirmed" for value in category_coverage.values()):
        coverage = "confirmed"
    elif any(value == "confirmed" for value in category_coverage.values()):
        coverage = "partial"
    else:
        coverage = "none"
    return {
        "coverage": coverage,
        # This field preserves the distinction between no required research and
        # required research that returned no usable evidence.
        "research_status": "required" if research_required else "not_required",
        "required_categories": categories,
        "category_coverage": category_coverage,
    }


def _validate_fixtures(fixtures: list[dict[str, Any]]) -> None:
    if len(fixtures) != 15:
        raise ValueError("daily paper run requires exactly 15 fixtures")
    ids = [str(row.get("match_id", "")) for row in fixtures]
    if any(not match_id for match_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("daily paper fixtures must have unique match_id values")
    expected = [f"M{i:02d}" for i in range(1, 16)]
    if ids != expected:
        raise ValueError("daily paper fixtures must preserve official M01-M15 order")
    for row in fixtures:
        if not row.get("home") or not row.get("away"):
            raise ValueError("daily paper fixtures require home and away")


def _coverage_by_match(fixtures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for fixture in fixtures:
        quality = fixture.get("data_quality", {})
        decision = decide_research(
            data_quality_score=float(quality.get("score", 0.0)),
            missing_fields=quality.get("missing_fields", []),
            stale_sources=quality.get("stale_sources", []),
            source_conflicts=quality.get("source_conflicts", []),
        )
        result[fixture["match_id"]] = classify_evidence_coverage(
            decision.research_required, decision.categories, fixture.get("evidence", {})
        )
    return result


def freeze_daily_run(
    *,
    run_id: str,
    fixtures: list[dict[str, Any]],
    manifest_path: str | Path,
    prediction_artifact: str,
    model_version: str,
    ensemble_version: str,
    calibration_version: str,
    decision_policy_version: str,
    h15_policy_version: str,
    research_configuration: Mapping[str, Any] | None = None,
    frozen_at: str | None = None,
) -> dict[str, Any]:
    """Create or idempotently reload the immutable pre-match run manifest."""
    _validate_fixtures(fixtures)
    coverage_by_match = _coverage_by_match(fixtures)
    counts = {level: sum(item["coverage"] == level for item in coverage_by_match.values()) for level in COVERAGE_LEVELS}
    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "run_type": "daily_paper_test",
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "official_order": [row["match_id"] for row in fixtures],
        "prediction_artifact": prediction_artifact,
        "model_version": model_version,
        "ensemble_version": ensemble_version,
        "calibration_version": calibration_version,
        "decision_policy_version": decision_policy_version,
        "h15_policy_version": h15_policy_version,
        "research_configuration": dict(research_configuration or {}),
        "evidence_coverage": {"counts": counts, "by_match": coverage_by_match},
        "frozen_at": frozen_at or datetime.now(timezone.utc).isoformat(),
        "status": "frozen_pre_match",
    }
    target = Path(manifest_path).expanduser()
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing != manifest:
            raise ValueError("paper run manifest is immutable and differs from requested run")
        return existing
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


__all__ = ["classify_evidence_coverage", "freeze_daily_run"]
