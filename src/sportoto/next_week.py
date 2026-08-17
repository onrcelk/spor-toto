"""Next-week, read-only team form and data coverage report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .current_list import load_current_list


def _result_points(result: str, home: bool) -> int:
    if result == "X":
        return 1
    if result == "1":
        return 3 if home else 0
    if result == "2":
        return 0 if home else 3
    return 0


def _team_summary(frame: pd.DataFrame, team: str, before: pd.Timestamp, last_n: int) -> dict[str, Any]:
    team_mask = (frame["home_team"].astype(str).str.casefold() == team.casefold()) | (frame["away_team"].astype(str).str.casefold() == team.casefold())
    eligible = frame[(frame["kickoff_iso"] < before) & team_mask].copy().sort_values("kickoff_iso").tail(last_n)
    matches = []
    points = 0
    for _, row in eligible.iterrows():
        is_home = str(row["home_team"]).casefold() == team.casefold()
        result_value = row["actual_1x2"]
        result = {0: "1", 1: "X", 2: "2"}.get(result_value, str(result_value))
        points += _result_points(result, is_home)
        matches.append({"kickoff_iso": row["kickoff_iso"].isoformat(), "opponent": row["away_team"] if is_home else row["home_team"], "venue": "H" if is_home else "A", "result": result})
    return {"team": team, "sample_size": len(matches), "points": points, "points_per_match": round(points / len(matches), 3) if matches else None, "recent_matches": matches}


def build_next_week_report(
    matches_path: Path | str = Path("data/current_sportoto_list.json"),
    history_path: Path | str = Path("data/sportoto_master_training.parquet"),
    output: Path | str = Path("data/next_week_analysis.json"),
    last_n: int = 5,
) -> dict[str, Any]:
    matches = load_current_list(matches_path)
    frame = pd.read_parquet(Path(history_path).expanduser())
    frame["kickoff_iso"] = pd.to_datetime(frame["kickoff_iso"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["kickoff_iso", "actual_1x2"])
    report_matches = []
    for item in matches:
        kickoff_text = item.get("date_text", item.get("date", ""))
        time_text = item.get("time_text", item.get("time", ""))
        kickoff = pd.to_datetime(f"{kickoff_text} {time_text}", dayfirst=True, utc=True, errors="coerce")
        if pd.isna(kickoff):
            kickoff = pd.Timestamp.now(tz="UTC")
        home = item["home_team"]
        away = item["away_team"]
        report_matches.append({"match_index": item["match_index"], "home_team": home, "away_team": away, "kickoff": kickoff.isoformat(), "home_form": _team_summary(frame, home, kickoff, last_n), "away_form": _team_summary(frame, away, kickoff, last_n)})
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "pre_match_read_only", "last_n": last_n, "match_count": len(report_matches), "matches": report_matches}
    target = Path(output).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


__all__ = ["build_next_week_report"]
