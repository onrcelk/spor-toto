"""Build a current-week model/market/Dixon-Coles comparison report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sportoto.ensemble import ensemble_probabilities, normalized_market_probabilities


def build(predictions_path: str, odds_path: str, output: str) -> dict:
    predictions = json.loads(Path(predictions_path).read_text(encoding="utf-8"))["predictions"]
    odds = {x["match_index"]: x for x in json.loads(Path(odds_path).read_text(encoding="utf-8"))["matches"]}
    rows = []
    for p in predictions:
        model = {"1": p["pred_home_win"], "X": p["pred_draw"], "2": p["pred_away_win"]}
        xg = p.get("features", {})
        market = None
        if p["match_index"] in odds:
            market = normalized_market_probabilities(odds[p["match_index"]]["odds"])
        ens = ensemble_probabilities(model, xg.get("home_xg_avg", 1.2), xg.get("away_xg_avg", 1.2), market)
        rows.append({
            "match_index": p["match_index"], "home_team": p["home_team"], "away_team": p["away_team"],
            "model": model, "market": market, "ensemble": {k: round(v, 4) for k, v in ens.items()},
            "ensemble_pick": max(ens, key=ens.get), "market_available": market is not None,
        })
    report = {"source_predictions": predictions_path, "source_odds": odds_path, "rows": rows,
              "market_rows": sum(r["market_available"] for r in rows), "total_rows": len(rows)}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--odds", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    r = build(args.predictions, args.odds, args.output)
    print(json.dumps({"total_rows": r["total_rows"], "market_rows": r["market_rows"], "output": args.output}, ensure_ascii=False))
