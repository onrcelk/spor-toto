"""Read-only adapters for public football data sources."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

JsonOpener = Callable[[urllib.request.Request], dict[str, Any]]


@dataclass(frozen=True)
class MatchRecord:
    source: str
    source_match_id: str
    home_team: str
    away_team: str
    match_date: str
    home_goals: int | None
    away_goals: int | None
    status: str
    over_under: str | None
    fetched_at: str

    @property
    def result(self) -> str | None:
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return "1"
        if self.home_goals < self.away_goals:
            return "2"
        return "X"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["result"] = self.result
        return data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_opener(request: urllib.request.Request) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _request_json(url: str, headers: dict[str, str], opener: JsonOpener | None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    return (opener or _default_opener)(request)


def _status(value: str | None) -> str:
    value = (value or "").upper()
    if value in {"FT", "FINISHED", "AET", "PEN"}:
        return "FINISHED"
    if value in {"LIVE", "IN_PLAY", "1H", "2H", "HT", "ET"}:
        return "LIVE"
    if value in {"PST", "POSTPONED", "CANCELLED", "SUSPENDED"}:
        return value
    return "SCHEDULED"


def _ou(home: int | None, away: int | None) -> str | None:
    if home is None or away is None:
        return None
    return "over" if home + away > 2.5 else "under"


def _record(source: str, match_id: Any, home: str, away: str, date: str,
            home_goals: Any, away_goals: Any, status: str, fetched_at: str) -> MatchRecord:
    return MatchRecord(
        source=source,
        source_match_id=str(match_id),
        home_team=home,
        away_team=away,
        match_date=date[:10],
        home_goals=home_goals if isinstance(home_goals, int) else None,
        away_goals=away_goals if isinstance(away_goals, int) else None,
        status=_status(status),
        over_under=_ou(home_goals if isinstance(home_goals, int) else None, away_goals if isinstance(away_goals, int) else None),
        fetched_at=fetched_at,
    )


def fetch_api_sports(date: str, api_key: str | None = None, base_url: str | None = None,
                     opener: JsonOpener | None = None, fetched_at: str | None = None) -> list[MatchRecord]:
    key = api_key or os.getenv("API_SPORTS_KEY", "")
    if not key:
        raise ValueError("API_SPORTS_KEY is required")
    base = (base_url or os.getenv("API_SPORTS_BASE_URL", "https://v3.football.api-sports.io")).rstrip("/")
    url = f"{base}/fixtures?{urllib.parse.urlencode({'date': date})}"
    payload = _request_json(url, {"x-apisports-key": key, "Accept": "application/json"}, opener)
    return [_record("api-sports", item.get("fixture", {}).get("id"),
                    item.get("teams", {}).get("home", {}).get("name", ""),
                    item.get("teams", {}).get("away", {}).get("name", ""),
                    item.get("fixture", {}).get("date", ""),
                    item.get("goals", {}).get("home"), item.get("goals", {}).get("away"),
                    item.get("fixture", {}).get("status", {}).get("short"), fetched_at or _now())
            for item in payload.get("response", [])]


def fetch_football_data(api_token: str | None = None, base_url: str | None = None,
                        opener: JsonOpener | None = None, fetched_at: str | None = None) -> list[MatchRecord]:
    token = api_token or os.getenv("FOOTBALL_DATA_API_TOKEN", "")
    if not token:
        raise ValueError("FOOTBALL_DATA_API_TOKEN is required")
    base = (base_url or os.getenv("FOOTBALL_DATA_BASE_URL", "https://api.football-data.org/v4")).rstrip("/")
    payload = _request_json(f"{base}/matches", {"X-Auth-Token": token, "Accept": "application/json"}, opener)
    records = []
    for item in payload.get("matches", []):
        score = item.get("score", {}).get("fullTime", {})
        records.append(_record("football-data.org", item.get("id"),
                               item.get("homeTeam", {}).get("name", ""),
                               item.get("awayTeam", {}).get("name", ""), item.get("utcDate", ""),
                               score.get("home"), score.get("away"), item.get("status"), fetched_at or _now()))
    return records


def parse_openfootball(payload: dict[str, Any], fetched_at: str | None = None) -> list[MatchRecord]:
    records = []
    for item in payload.get("matches", []):
        score = item.get("score") or {}
        ft = score.get("ft") or []
        home = ft[0] if len(ft) > 0 and isinstance(ft[0], int) else None
        away = ft[1] if len(ft) > 1 and isinstance(ft[1], int) else None
        records.append(_record("openfootball", f"{item.get('team1','')}-{item.get('team2','')}-{item.get('date','')}",
                               item.get("team1", ""), item.get("team2", ""), item.get("date", ""),
                               home, away, "FINISHED" if home is not None and away is not None else "SCHEDULED",
                               fetched_at or _now()))
    return records


def fetch_openfootball(url: str, opener: JsonOpener | None = None,
                       fetched_at: str | None = None) -> list[MatchRecord]:
    payload = _request_json(url, {"Accept": "application/json"}, opener)
    return parse_openfootball(payload, fetched_at=fetched_at)


__all__ = ["MatchRecord", "fetch_api_sports", "fetch_football_data", "fetch_openfootball", "parse_openfootball"]
