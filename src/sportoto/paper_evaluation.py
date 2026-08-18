"""Deterministic aggregate metrics for frozen paper-test audit artifacts."""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from .calibration import brier_score_multiclass, log_loss_score

RESULT_INDEX = {"1": 0, "X": 1, "2": 2}
COVERAGE_LEVELS = ("none", "partial", "confirmed")


def _rate(hit: int, total: int) -> float | None:
    return round(hit / total, 6) if total else None


def _metric(rows: list[Mapping[str, Any]], field: str) -> dict[str, Any]:
    values = [row[field] for row in rows if row.get(field) is not None]
    hit = sum(bool(value) for value in values)
    return {"hits": hit, "count": len(values), "accuracy": _rate(hit, len(values))}


def _probability_metric(rows: list[Mapping[str, Any]], path: tuple[str, ...]) -> dict[str, Any]:
    probabilities = []
    labels = []
    for row in rows:
        value: Any = row
        for key in path:
            value = value.get(key) if isinstance(value, Mapping) else None
        actual = row.get("post_match", {}).get("actual")
        if isinstance(value, Mapping) and actual in RESULT_INDEX:
            probabilities.append([float(value[key]) for key in ("1", "X", "2")])
            labels.append(RESULT_INDEX[actual])
    if not labels:
        return {"sample_size": 0, "brier": None, "log_loss": None}
    return {
        "sample_size": len(labels),
        "brier": round(brier_score_multiclass(probabilities, labels), 6),
        "log_loss": round(log_loss_score(probabilities, labels), 6),
    }


def evaluate_paper_runs(
    records: Iterable[Mapping[str, Any]],
    h15_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows = list(records)
    final = [row for row in rows if row.get("post_match", {}).get("result_status") == "final_verified"
             and row.get("post_match", {}).get("actual") in RESULT_INDEX]
    coverage_counts = Counter(
        row.get("research", {}).get("evidence_coverage", {}).get("coverage", "none")
        for row in rows
    )
    banko_rows = [row for row in final if row.get("decision", {}).get("banko")]
    double_rows = [row for row in final if len(str(row.get("decision", {}).get("selection", ""))) == 2]
    triple_rows = [row for row in final if row.get("decision", {}).get("selection") == "1X2"]
    return {
        "matches_total": len(rows),
        "final_results": len(final),
        "decision_hit": _metric(final, "decision_hit"),
        "coupon_covered": _metric(final, "coupon_covered"),
        "banko": {"count": len(banko_rows), **_metric(banko_rows, "decision_hit")},
        "double": {"count": len(double_rows), **_metric(double_rows, "coupon_covered")},
        "triple": {"count": len(triple_rows), **_metric(triple_rows, "coupon_covered")},
        "h15": {
            "all_scenario_coverage": h15_audit.get("actual_in_all_scenarios") if h15_audit else None,
            "filtered_coverage": h15_audit.get("actual_in_filtered") if h15_audit else None,
            "filter_elimination": h15_audit.get("eliminated_by") if h15_audit else None,
        },
        "calibration": {
            "raw": _probability_metric(final, ("prediction", "raw")),
            "calibrated": _probability_metric(final, ("prediction", "calibrated")),
            "ensemble": _probability_metric(final, ("ensemble",)),
        },
        "evidence_coverage": {level: coverage_counts.get(level, 0) for level in COVERAGE_LEVELS},
    }


__all__ = ["evaluate_paper_runs"]
