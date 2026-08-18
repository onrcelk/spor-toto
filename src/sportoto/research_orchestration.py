"""Research orchestration and evidence validation for match decisions."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    match_id: str
    claim: str
    category: str
    source: str
    source_url: str | None
    source_reliability: float
    published_at: str | None
    retrieved_at: str
    freshness: str
    verified: bool
    details: dict[str, Any] | None = None

    @classmethod
    def create(cls, match_id: str, claim: str, category: str, source: str,
               *, source_url: str | None = None, source_reliability: float = 0.5,
               published_at: str | None = None, freshness: str = "unknown",
               verified: bool = False, details: dict[str, Any] | None = None) -> "Evidence":
        raw = "|".join([match_id, category, claim, source, source_url or ""])
        evidence_id = "EVIDENCE_" + hashlib.sha256(raw.encode()).hexdigest()[:12]
        return cls(evidence_id, match_id, claim, category, source, source_url,
                   round(float(source_reliability), 4), published_at,
                   datetime.now(timezone.utc).isoformat(), freshness, verified, details)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchDecision:
    research_required: bool
    priority: str
    categories: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_research(
    *,
    data_quality_score: float,
    missing_fields: Iterable[str] = (),
    stale_sources: Iterable[str] = (),
    source_conflicts: Iterable[str] = (),
) -> ResearchDecision:
    missing = set(missing_fields)
    stale = set(stale_sources)
    conflicts = set(source_conflicts)
    categories: set[str] = set()
    reasons: list[str] = []
    if "market_odds" in missing:
        categories.add("odds"); reasons.append("missing_market_odds")
    if "lineup" in missing or "squad" in missing:
        categories.add("squad"); reasons.append("missing_squad_or_lineup")
    if "news" in missing:
        categories.add("news"); reasons.append("missing_news")
    for source in stale:
        categories.add(source if source in {"odds", "squad", "news", "form", "transfer"} else "refresh")
        reasons.append(f"stale_{source}")
    for category in conflicts:
        categories.add(category)
        reasons.append(f"conflicting_{category}")
    if float(data_quality_score) < 0.85:
        reasons.append("low_data_quality")
        if not categories:
            categories.add("general_validation")
    priority = "high" if conflicts or {"odds", "squad", "news"} & categories else ("medium" if categories else "none")
    return ResearchDecision(bool(categories), priority, tuple(sorted(categories)), tuple(sorted(set(reasons))))


def append_evidence(path: str | Path, evidence: Evidence) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(evidence.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def validate_evidence(evidence: Iterable[Evidence]) -> dict[str, Any]:
    items = list(evidence)
    if not items:
        return {"verified": False, "reliability": 0.0, "agreement": "none", "count": 0, "evidence_ids": []}
    reliable = [e for e in items if e.verified and e.freshness == "fresh"]
    sources = {e.source for e in reliable}
    claims = {e.claim.strip().casefold() for e in reliable}
    reliability = sum(e.source_reliability for e in reliable) / len(reliable) if reliable else 0.0
    if len(claims) > 1:
        agreement = "conflicted"
    else:
        agreement = "confirmed" if len(sources) >= 2 else ("single_source" if reliable else "unverified")
    return {
        "verified": len(reliable) >= 2 and len(claims) <= 1,
        "reliability": round(reliability, 4),
        "agreement": agreement,
        "count": len(items),
        "reliable_count": len(reliable),
        "evidence_ids": [e.evidence_id for e in items],
    }


def apply_research_to_journal(record: dict[str, Any], evidence: Iterable[Evidence]) -> dict[str, Any]:
    items = list(evidence)
    updated = json.loads(json.dumps(record))
    by_category: dict[str, list[Evidence]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)
    summary = {}
    for category, category_items in by_category.items():
        summary[category] = validate_evidence(category_items)
    updated["evidence"] = [item.to_dict() for item in items]
    updated["evidence_validation"] = summary
    updated.setdefault("risk", {}).setdefault("flags", [])
    for category, result in summary.items():
        updated.setdefault("source_reliability", {})[category] = {
            "level": "high" if result["reliability"] >= .85 else ("medium" if result["reliability"] >= .60 else "low"),
            "score": result["reliability"],
        }
        if result["agreement"] == "conflicted":
            flag = f"{category}_source_conflict"
        elif not result["verified"]:
            flag = f"{category}_evidence_unconfirmed"
        else:
            flag = None
        if flag and flag not in updated["risk"]["flags"]:
            updated["risk"]["flags"].append(flag)
            updated["risk"]["banko_allowed"] = False
    updated["research"] = {"evidence_count": len(items), "categories": sorted(by_category)}
    return updated


__all__ = ["Evidence", "ResearchDecision", "append_evidence", "apply_research_to_journal", "decide_research", "validate_evidence"]
