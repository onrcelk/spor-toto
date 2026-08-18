"""Append-only, auditable decision journal for Sport Toto matches."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
RESULTS = {"1", "X", "2"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_reliability(level: str, score: float) -> dict[str, Any]:
    if level not in {"high", "medium", "low"}:
        raise ValueError("source reliability level must be high, medium or low")
    if not 0.0 <= float(score) <= 1.0:
        raise ValueError("source reliability score must be between 0 and 1")
    return {"level": level, "score": round(float(score), 4)}


def build_decision_record(
    run_id: str,
    match_id: str,
    fixture: dict[str, Any],
    model_signals: dict[str, dict[str, Any]],
    raw_probabilities: dict[str, float],
    calibrated_probabilities: dict[str, float],
    decision: dict[str, Any],
    *,
    data_quality: dict[str, Any] | None = None,
    reliability: dict[str, dict[str, Any]] | None = None,
    risk: dict[str, Any] | None = None,
    coupon: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if set(raw_probabilities) != RESULTS or set(calibrated_probabilities) != RESULTS:
        raise ValueError("probabilities must contain exactly 1, X and 2")
    if sum(float(v) for v in calibrated_probabilities.values()) <= 0:
        raise ValueError("calibrated probabilities must have positive sum")
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _now(),
        "run_id": run_id,
        "match_id": match_id,
        "fixture": fixture,
        "data_quality": data_quality or {
            "score": 0.0, "cold_start": True, "missing_fields": [], "stale_sources": [],
        },
        "source_reliability": reliability or {},
        "model_signals": model_signals,
        "prediction": {
            "raw": {k: round(float(v), 6) for k, v in raw_probabilities.items()},
            "calibrated": {k: round(float(v), 6) for k, v in calibrated_probabilities.items()},
        },
        "risk": risk or {"level": "unknown", "flags": [], "banko_allowed": False},
        "decision": decision,
        "coupon": coupon or {"option_set": None, "filter_status": None},
        "post_match": {"actual": None, "hit": None, "error_type": None},
    }


def append_decision_record(path: str | Path, record: dict[str, Any]) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def update_post_match(record: dict[str, Any], actual: str, error_type: str | None = None) -> dict[str, Any]:
    if actual not in RESULTS:
        raise ValueError("actual result must be 1, X or 2")
    updated = json.loads(json.dumps(record))
    selection = updated.get("decision", {}).get("selection", "")
    hit = actual in set(selection.replace("/", ""))
    updated["post_match"] = {"actual": actual, "hit": hit, "error_type": None if hit else error_type}
    updated["post_match"]["audited_at"] = _now()
    return updated


__all__ = ["append_decision_record", "build_decision_record", "source_reliability", "update_post_match"]
