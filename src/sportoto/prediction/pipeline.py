"""Adapters for existing prediction artifacts; no new model is trained here."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RESULTS = {"1", "X", "2"}


def _probabilities(raw: dict[str, Any]) -> dict[str, float]:
    values = {k: float(raw[k]) for k in RESULTS}
    if any(value < 0 for value in values.values()) or sum(values.values()) <= 0:
        raise ValueError("prediction probabilities must be non-negative with positive sum")
    total = sum(values.values())
    return {key: value / total for key, value in values.items()}


def load_prediction_artifact(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("predictions", payload.get("rows", []))
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        match_id = str(row.get("match_id") or f"M{int(row['match_index']):02d}")
        if "model" in row:
            model = _probabilities(row["model"])
        else:
            model = _probabilities({"1": row["pred_home_win"], "X": row["pred_draw"], "2": row["pred_away_win"]})
        result: dict[str, Any] = {"match_id": match_id, "model": model, "features": row.get("features", {})}
        if row.get("market"):
            result["market"] = _probabilities(row["market"])
        if row.get("ensemble"):
            result["ensemble"] = _probabilities(row["ensemble"])
        output[match_id] = result
    return output


__all__ = ["load_prediction_artifact"]
