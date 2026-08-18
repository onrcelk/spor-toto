"""Project completed workflow state into idempotent audit journal records."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .orchestration.state import WorkflowState
from .paper_testing import classify_evidence_coverage

REQUIRED = ("prediction", "calibration", "ensemble", "risk", "decision")


def project_state(state: WorkflowState) -> list[dict[str, Any]]:
    if not all(stage in state.stage_history for stage in REQUIRED):
        raise ValueError(f"workflow missing final stages: {REQUIRED}")
    ids = [fixture["match_id"] for fixture in state.fixtures]
    maps = [{row["match_id"]: row for row in rows} for rows in (state.model_predictions, state.calibrated_predictions, state.ensemble, state.risk, state.decisions)]
    if any(set(mapping) != set(ids) for mapping in maps):
        raise ValueError("journal projection requires exact fixture coverage at every stage")
    evidence_by_match: dict[str, list[dict[str, Any]]] = {match_id: [] for match_id in ids}
    for item in state.evidence:
        if item["match_id"] in evidence_by_match:
            evidence_by_match[item["match_id"]].append(item)
    research_by_match = {row["match_id"]: row for row in state.research_decisions}
    records = []
    for match_id in ids:
        raw = maps[0][match_id]["model"]
        calibrated = maps[1][match_id]["calibrated"]
        risk = maps[3][match_id]
        decision = maps[4][match_id]
        research_decision = research_by_match.get(match_id, {})
        coverage = classify_evidence_coverage(
            bool(research_decision.get("research_required", False)),
            research_decision.get("categories", ()),
            {category: [item for item in evidence_by_match[match_id] if item.get("category") == category]
             for category in research_decision.get("categories", ())},
        )
        records.append({
            "record_id": f"{state.run_id}:{match_id}:v1", "schema_version": "2.0", "run_id": state.run_id,
            "match_id": match_id, "fixture": next(f for f in state.fixtures if f["match_id"] == match_id),
            "prediction": {"raw": raw, "calibrated": calibrated},
            "ensemble": maps[2][match_id]["output"], "ensemble_metadata": state.ensemble_metadata,
            "risk": {"level": risk["risk_level"], "confidence": risk["confidence"], "score": risk["risk_score"], "flags": risk["flags"], "banko_allowed": risk["banko_allowed"]},
            "decision": {key: decision[key] for key in ("selection", "primary", "secondary", "confidence", "banko", "reasons")},
            "research": {
                "evidence_ids": sorted(item["evidence_id"] for item in evidence_by_match[match_id]),
                "evidence_coverage": coverage,
                "stages_completed": list(state.stage_history),
            },
            "post_match": {"actual": None, "hit": None, "error_type": None, "audit_at": None},
        })
    return records


def write_idempotent(path: str | Path, records: list[dict[str, Any]]) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    unique = {record["record_id"]: record for record in records}
    target.write_text("\n".join(json.dumps(unique[key], ensure_ascii=False, sort_keys=True) for key in sorted(unique)) + "\n", encoding="utf-8")


__all__ = ["project_state", "write_idempotent"]
