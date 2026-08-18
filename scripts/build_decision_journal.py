"""Convert an ensemble report into append-only Decision Journal records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sportoto.decision_journal import append_decision_record, build_decision_record, source_reliability


def build(ensemble_path: str, output: str, run_id: str) -> int:
    report = json.loads(Path(ensemble_path).read_text(encoding="utf-8"))
    target = Path(output).expanduser()
    if target.exists():
        target.unlink()
    count = 0
    for row in report["rows"]:
        market_available = bool(row["market_available"])
        ens = row["ensemble"]
        model = row["model"]
        selection = row["ensemble_pick"]
        if max(ens.values()) < 0.50:
            selection = "1X2"
        risk_flags = []
        if not market_available:
            risk_flags.append("missing_market_odds")
        if row["match_index"] in {1, 4, 11, 13}:
            risk_flags.append("friday_or_opening_week")
        record = build_decision_record(
            run_id, f"M{row['match_index']:02d}",
            {"home": row["home_team"], "away": row["away_team"], "competition": "Spor Toto"},
            {"gbm_transfer_or_general": {"prediction": max(model, key=model.get), "probabilities": model},
             "market": {"prediction": max(row["market"], key=row["market"].get), "probabilities": row["market"]}
             if market_available else {"prediction": None, "probabilities": None},
             "ensemble": {"prediction": selection, "probabilities": ens}},
            model, ens,
            {"selection": selection, "confidence": "medium" if max(ens.values()) >= .50 else "low",
             "reasons": ["ensemble generated from available model/market signals"]},
            data_quality={"score": .85 if market_available else .60, "cold_start": False,
                          "missing_fields": [] if market_available else ["market_odds"], "stale_sources": []},
            reliability={"model": source_reliability("medium", .70),
                         "odds": source_reliability("high", .94) if market_available else source_reliability("low", .20)},
            risk={"level": "medium" if market_available else "high", "flags": risk_flags,
                  "banko_allowed": selection in {"1", "X", "2"} and not risk_flags},
        )
        append_decision_record(target, record)
        count += 1
    return count


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    print(json.dumps({"records": build(args.ensemble, args.output, args.run_id), "output": args.output}))
