"""Read-only periodic snapshots for match-day monitoring."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .masha_integration import SportotoMatchRow, fetch_sportoto_list
from .tff_integration import TFFMatchRow, fetch_results


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _append_if_changed(path: Path, payload: dict[str, Any], fingerprint: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if path.exists():
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if line.strip():
                try:
                    previous = json.loads(line).get("fingerprint")
                except json.JSONDecodeError:
                    pass
                break
    changed = previous != fingerprint
    payload["changed"] = changed
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return changed


def snapshot_sportoto_list(
    output: Path | str = Path("data/live/sportoto_list_snapshots.jsonl"),
    fetcher: Callable[[], Iterable[SportotoMatchRow]] = fetch_sportoto_list,
) -> dict[str, Any]:
    rows = [asdict(row) for row in fetcher()]
    if not rows:
        raise RuntimeError("Resmi Spor Toto listesi boş döndü; snapshot yazılmadı.")
    fingerprint = hashlib.sha256(_canonical(rows).encode()).hexdigest()
    payload = {"observed_at": _now(), "source": "sportoto.gov.tr", "match_count": len(rows), "fingerprint": fingerprint, "matches": rows}
    changed = _append_if_changed(Path(output).expanduser(), payload, fingerprint)
    payload["changed"] = changed
    return payload


def snapshot_tff_results(
    output: Path | str = Path("data/live/tff_result_snapshots.jsonl"),
    fetcher: Callable[[], Iterable[TFFMatchRow]] = fetch_results,
) -> dict[str, Any]:
    rows = [asdict(row) for row in fetcher()]
    if not rows:
        raise RuntimeError("TFF sonuç kaynağı boş döndü; snapshot yazılmadı.")
    fingerprint = hashlib.sha256(_canonical(rows).encode()).hexdigest()
    payload = {"observed_at": _now(), "source": "tff.org", "match_count": len(rows), "fingerprint": fingerprint, "results": rows}
    changed = _append_if_changed(Path(output).expanduser(), payload, fingerprint)
    payload["changed"] = changed
    return payload


def collect_live(
    output_dir: Path | str = Path("data/live"),
    include_tff: bool = True,
) -> dict[str, Any]:
    directory = Path(output_dir).expanduser()
    result: dict[str, Any] = {"collected_at": _now(), "sources": {}}
    try:
        result["sources"]["sportoto"] = snapshot_sportoto_list(directory / "sportoto_list_snapshots.jsonl")
    except Exception as exc:
        result["sources"]["sportoto"] = {"error": str(exc), "changed": False}
    if include_tff:
        try:
            result["sources"]["tff"] = snapshot_tff_results(directory / "tff_result_snapshots.jsonl")
        except Exception as exc:
            result["sources"]["tff"] = {"error": str(exc), "changed": False}
    result["changed"] = any(v.get("changed", False) for v in result["sources"].values())
    return result


__all__ = ["snapshot_sportoto_list", "snapshot_tff_results", "collect_live"]
