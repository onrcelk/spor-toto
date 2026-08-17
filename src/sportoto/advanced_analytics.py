"""StatsBomb Open Data event parser for advanced, source-grounded metrics."""
from __future__ import annotations

import json
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ShotRecord:
    team: str
    player: str | None
    x: float | None
    y: float | None
    xg: float | None
    outcome: str | None
    body_part: str | None
    technique: str | None
    freeze_frame_count: int


@dataclass(frozen=True)
class StatsBombMetrics:
    xg_by_team: dict[str, float]
    xa_by_team: dict[str, float]
    ppda_by_team: dict[str, float]
    shots: list[ShotRecord]
    key_passes_by_team: dict[str, int]
    defensive_actions_by_team: dict[str, int]
    event_count: int


def _name(value: Any) -> str | None:
    return value.get("name") if isinstance(value, dict) else None


def _location(value: Any) -> tuple[float | None, float | None]:
    if not isinstance(value, list) or len(value) < 2:
        return None, None
    x, y = value[0], value[1]
    return (x if isinstance(x, (int, float)) else None,
            y if isinstance(y, (int, float)) else None)


def parse_statsbomb_events(events: list[dict[str, Any]]) -> StatsBombMetrics:
    xg: dict[str, float] = defaultdict(float)
    xa: dict[str, float] = defaultdict(float)
    ppda: dict[str, float] = {}
    key_passes: dict[str, int] = defaultdict(int)
    defensive_actions: dict[str, int] = defaultdict(int)
    shots: list[ShotRecord] = []
    defensive_types = {"Pressure", "Tackle", "Interception", "Block", "Clearance", "Foul Committed", "Duel"}

    for event in events:
        team = _name(event.get("team")) or "Unknown"
        event_type = _name(event.get("type")) or ""
        if event_type == "Shot":
            shot = event.get("shot") or {}
            raw_xg = shot.get("statsbomb_xg")
            shot_xg = float(raw_xg) if isinstance(raw_xg, (int, float)) else None
            if shot_xg is not None:
                xg[team] += shot_xg
            x, y = _location(event.get("location"))
            freeze = shot.get("freeze_frame")
            shots.append(ShotRecord(
                team=team,
                player=_name(event.get("player")),
                x=x,
                y=y,
                xg=shot_xg,
                outcome=_name(shot.get("outcome")),
                body_part=_name(shot.get("body_part")),
                technique=_name(shot.get("technique")),
                freeze_frame_count=len(freeze) if isinstance(freeze, list) else 0,
            ))
        if event_type == "Pass" and (event.get("pass") or {}).get("shot_assist") is True:
            key_passes[team] += 1
        if event_type in defensive_types:
            defensive_actions[team] += 1
        raw_xa = event.get("statsbomb_xa")
        if not isinstance(raw_xa, (int, float)):
            raw_xa = (event.get("pass") or {}).get("xa")
        if isinstance(raw_xa, (int, float)):
            xa[team] += float(raw_xa)
        raw_ppda = event.get("ppda")
        if isinstance(raw_ppda, (int, float)):
            ppda[team] = float(raw_ppda)

    return StatsBombMetrics(
        xg_by_team=dict(xg),
        xa_by_team=dict(xa),
        ppda_by_team=ppda,
        shots=shots,
        key_passes_by_team=dict(key_passes),
        defensive_actions_by_team=dict(defensive_actions),
        event_count=len(events),
    )


def fetch_statsbomb_events(url: str, opener: Callable[[str], Any] | None = None) -> list[dict[str, Any]]:
    if opener is not None:
        payload = opener(url)
    else:
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.loads(response.read())
    if not isinstance(payload, list):
        raise ValueError("StatsBomb event payload must be a JSON list")
    return payload


__all__ = ["ShotRecord", "StatsBombMetrics", "fetch_statsbomb_events", "parse_statsbomb_events"]
