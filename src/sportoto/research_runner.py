"""Deterministic Research Decision -> Registry -> Evidence -> Journal runner."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapter_contracts import AdapterRegistry
from .odds_adapter import OddsAdapter
from .odds_providers import TelegramStaticOddsProvider
from .research_orchestration import apply_research_to_journal


def run(journal_path: str, odds_path: str, output_path: str) -> dict[str, Any]:
    source = json.loads(Path(odds_path).read_text(encoding="utf-8"))
    rows = [dict(row, match_id=f"M{int(row['match_index']):02d}") for row in source.get("matches", [])]
    registry = AdapterRegistry()
    registry.register(OddsAdapter(TelegramStaticOddsProvider(rows)))
    records = []
    odds_found = market_available = verified = research_required = 0
    for line in Path(journal_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        result = registry.retrieve(["odds"], record["match_id"], {"freshness": "unknown"})[0]
        if result.status == "success":
            odds_found += 1
        evidence = list(result.evidence)
        if evidence and evidence[0].details and evidence[0].details.get("market_available"):
            market_available += 1
        if evidence and evidence[0].verified:
            verified += 1
        if result.status != "success":
            research_required += 1
        updated = apply_research_to_journal(record, evidence)
        updated.setdefault("research", {})["retrieval"] = {"category": "odds", "status": result.status, "error": result.error}
        records.append(updated)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records) + "\n", encoding="utf-8")
    return {"matches": len(records), "odds_found": odds_found, "market_available": market_available,
            "verified": verified, "research_required": research_required, "output": str(target)}
