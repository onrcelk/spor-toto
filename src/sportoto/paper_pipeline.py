"""Batch collection and persistence around frozen paper-test audits."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .paper_audit import audit_frozen_journal


def collect_and_persist_audit(
    records: Iterable[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    played_option_sets: Mapping[str, Iterable[str]],
    output_path: str | Path,
    *,
    audited_at: str | None = None,
) -> list[dict[str, Any]]:
    """Audit a frozen batch and persist the derived artifact as canonical JSONL."""
    target = Path(output_path).expanduser()
    if audited_at is None and target.exists():
        existing_lines = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        if existing_lines:
            audited_at = json.loads(existing_lines[0]).get("post_match", {}).get("audited_at")
    audited = audit_frozen_journal(records, results, played_option_sets, audited_at=audited_at)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in audited) + "\n",
        encoding="utf-8",
    )
    return audited


def load_audit_artifact(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in Path(path).expanduser().read_text(encoding="utf-8").splitlines() if line.strip()
    ]


__all__ = ["collect_and_persist_audit", "load_audit_artifact"]
