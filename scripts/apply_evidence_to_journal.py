"""Apply validated evidence records to an existing Decision Journal JSONL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sportoto.research_orchestration import Evidence, apply_research_to_journal


def run(journal_path: str, evidence_path: str, output_path: str) -> int:
    evidence_by_match: dict[str, list[Evidence]] = {}
    for line in Path(evidence_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        evidence_by_match.setdefault(raw["match_id"], []).append(Evidence(**raw))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as fh:
        for line in Path(journal_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            updated = apply_research_to_journal(record, evidence_by_match.get(record["match_id"], []))
            fh.write(json.dumps(updated, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    print(json.dumps({"records": run(args.journal, args.evidence, args.output), "output": args.output}))
