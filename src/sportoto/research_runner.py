"""Deterministic Research Decision -> Registry -> Evidence -> Journal runner."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapter_contracts import AdapterRegistry
from .odds_adapter import OddsAdapter
from .odds_providers import TelegramStaticOddsProvider
from .research_orchestration import apply_research_to_journal
from .squad_adapter import SquadAdapter
from .squad_providers import StaticSquadProvider


def run(journal_path: str, odds_path: str, output_path: str, squad_path: str | None = None) -> dict[str, Any]:
    source = json.loads(Path(odds_path).read_text(encoding="utf-8"))
    rows = [dict(row, match_id=f"M{int(row['match_index']):02d}") for row in source.get("matches", [])]
    registry = AdapterRegistry()
    registry.register(OddsAdapter(TelegramStaticOddsProvider(rows)))
    if squad_path:
        squad_source = json.loads(Path(squad_path).read_text(encoding="utf-8"))
        registry.register(SquadAdapter(StaticSquadProvider(squad_source.get("matches", []), source=squad_source.get("source", "static_squad"))))
    records = []
    counts = {"odds_found": 0, "market_available": 0, "verified": 0, "research_required": 0, "squad_found": 0, "squad_evidence": 0}
    for line in Path(journal_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        categories = ["odds"] + (["squad"] if squad_path else [])
        results = registry.retrieve(categories, record["match_id"], {"freshness": "unknown"})
        evidence = []
        retrieval = []
        for result in results:
            retrieval.append({"category": result.category, "status": result.status, "error": result.error})
            evidence.extend(result.evidence)
            if result.category == "odds":
                if result.status == "success": counts["odds_found"] += 1
                if result.evidence and result.evidence[0].details and result.evidence[0].details.get("market_available"): counts["market_available"] += 1
                if result.evidence and result.evidence[0].verified: counts["verified"] += 1
                if result.status != "success": counts["research_required"] += 1
            elif result.category == "squad":
                if result.status == "success": counts["squad_found"] += 1
                counts["squad_evidence"] += len(result.evidence)
        updated = apply_research_to_journal(record, evidence)
        updated.setdefault("research", {})["retrieval"] = retrieval
        records.append(updated)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records) + "\n", encoding="utf-8")
    return {"matches": len(records), **counts, "output": str(target)}
