"""Current Spor Toto list snapshot and multi-competition training helpers."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .masha_integration import SportotoMatchRow, fetch_sportoto_list


def save_current_list(path: Path | str = Path("data/current_sportoto_list.json")) -> list[dict[str, Any]]:
    rows = fetch_sportoto_list()
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "match_count": len(rows),
        "matches": [asdict(row) for row in rows],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload["matches"]


def load_current_list(path: Path | str = Path("data/current_sportoto_list.json")) -> list[dict[str, Any]]:
    target = Path(path).expanduser()
    if not target.exists():
        return []
    payload = json.loads(target.read_text(encoding="utf-8"))
    return payload.get("matches", []) if isinstance(payload, dict) else []


__all__ = ["save_current_list", "load_current_list"]
