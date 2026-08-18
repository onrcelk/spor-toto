"""Deterministic category-driven Research -> Registry -> Journal runner."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapter_contracts import AdapterRegistry
from .news_adapter import NewsAdapter
from .news_providers import StaticNewsProvider
from .odds_adapter import OddsAdapter
from .odds_providers import TelegramStaticOddsProvider
from .research_orchestration import apply_research_to_journal
from .squad_adapter import SquadAdapter
from .squad_providers import StaticSquadProvider


def run(journal_path: str, odds_path: str, output_path: str, squad_path: str | None = None,
        news_path: str | None = None, max_attempts: dict[str, int] | None = None) -> dict[str, Any]:
    odds_source = json.loads(Path(odds_path).read_text(encoding="utf-8"))
    rows = [dict(row, match_id=f"M{int(row['match_index']):02d}") for row in odds_source.get("matches", [])]
    registry = AdapterRegistry()
    registry.register(OddsAdapter(TelegramStaticOddsProvider(rows)))
    optional = {}
    if squad_path:
        source = json.loads(Path(squad_path).read_text(encoding="utf-8"))
        registry.register(SquadAdapter(StaticSquadProvider(source.get("matches", []), source.get("source", "static_squad"))))
        optional["squad"] = source
    if news_path:
        source = json.loads(Path(news_path).read_text(encoding="utf-8"))
        registry.register(NewsAdapter(StaticNewsProvider(source.get("matches", []), source.get("source", "static_news"))))
        optional["news"] = source
    categories = ["odds", *optional.keys()]
    limits = max_attempts or {category: 1 for category in categories}
    records = []
    counts: dict[str, int] = {"odds_found": 0, "market_available": 0, "verified": 0, "research_required": 0}
    for category in optional:
        counts[f"{category}_found"] = 0
        counts[f"{category}_evidence"] = 0
    for line in Path(journal_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        results = registry.retrieve(categories, record["match_id"], {"freshness": "unknown", "max_attempts": limits})
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
            elif result.category in optional:
                if result.status == "success": counts[f"{result.category}_found"] += 1
                counts[f"{result.category}_evidence"] += len(result.evidence)
        updated = apply_research_to_journal(record, evidence)
        updated.setdefault("research", {})["retrieval"] = retrieval
        updated["research"]["categories"] = categories
        records.append(updated)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records) + "\n", encoding="utf-8")
    return {"matches": len(records), **counts, "categories": categories, "output": str(target)}
