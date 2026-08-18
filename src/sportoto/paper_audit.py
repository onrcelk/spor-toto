"""Read-only post-match audit for frozen paper-test journal records."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .h15 import actual_audit

FINAL_STATUS = "final_verified"
KNOWN_STATUS = {FINAL_STATUS, "live", "not_started", "postponed", "unknown"}


def audit_h15_survival(
    all_scenarios: list[dict[str, str]],
    filtered_scenarios: list[dict[str, str]],
    actual: dict[str, str],
    filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return H15 survival without changing scenarios or filters."""
    return actual_audit(all_scenarios, filtered_scenarios, actual, filters)


def _error_type(primary: str | None, actual: str, covered: bool, banko: bool) -> str | None:
    if not covered:
        return "coverage_failure"
    if banko and primary != actual:
        return "banko_miss"
    if primary == actual:
        return None
    if actual == "X":
        return "missed_draw"
    if primary in {"1", "2"} and actual in {"1", "2"} and primary != actual:
        return "missed_upset"
    return "wrong_direction"


def audit_frozen_journal(
    records: Iterable[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    played_option_sets: Mapping[str, Iterable[str]],
    *,
    audited_at: str | None = None,
) -> list[dict[str, Any]]:
    """Attach final results to frozen records; never recompute decisions."""
    timestamp = audited_at or datetime.now(timezone.utc).isoformat()
    audited = []
    for original in records:
        record = copy.deepcopy(dict(original))
        match_id = str(record["match_id"])
        result = results.get(match_id, {"actual": None, "status": "unknown"})
        status = result.get("status", "unknown")
        if status not in KNOWN_STATUS:
            raise ValueError(f"unknown result status: {status}")
        actual = result.get("actual")
        if status == FINAL_STATUS and actual not in {"1", "X", "2"}:
            raise ValueError("final_verified result must be 1, X or 2")
        if status != FINAL_STATUS:
            decision_hit = coupon_covered = None
            error_type = "postponed" if status == "postponed" else "pending"
            hit = None
        else:
            options = {str(option) for option in played_option_sets.get(match_id, ())}
            primary = record.get("decision", {}).get("primary")
            decision_hit = primary == actual
            coupon_covered = actual in options
            error_type = _error_type(primary, actual, coupon_covered, bool(record.get("decision", {}).get("banko")))
            hit = coupon_covered
        record["decision_hit"] = decision_hit
        record["coupon_covered"] = coupon_covered
        record["post_match"] = {
            "actual": actual,
            "result_status": status,
            "hit": hit,
            "error_type": error_type,
            "source": result.get("source"),
            "audited_at": timestamp,
        }
        audited.append(record)
    return audited


__all__ = ["audit_frozen_journal", "audit_h15_survival"]
