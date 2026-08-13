"""TFF-backed historical match data integration.

Reads match results, fixtures, and league tables from TFF.org
and stores them as structured JSONL records for model training.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tff.org"
LIVE_URL = f"{BASE_URL}/default.aspx?pageID=197"
FIXTURE_URL = f"{BASE_URL}/default.aspx?pageID=198"


@dataclass(frozen=True)
class TFFMatchRow:
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff_iso: str
    home_goals: int | None = None
    away_goals: int | None = None
    result: str | None = None


def _http_get_text(url: str, *, timeout: int = 30) -> str:
    try:
        response = requests.get(url, timeout=timeout, verify=False)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"TFF verisi çekilemedi: {url} ({exc})") from exc


def _parse_fixture_table(html: str) -> list[TFFMatchRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[TFFMatchRow] = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not headers:
            continue
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < 4:
                continue
            home = cells[0].strip()
            away = cells[2].strip() if len(cells) > 2 else ""
            date_text = cells[3].strip() if len(cells) > 3 else ""
            time_text = cells[4].strip() if len(cells) > 4 else ""
            if not home or not away:
                continue
            kickoff_iso = _try_parse_datetime(date_text, time_text)
            match_id = _slugify(home, away, date_text)
            rows.append(
                TFFMatchRow(
                    match_id=match_id,
                    home_team=home,
                    away_team=away,
                    league="TFF",
                    kickoff_iso=kickoff_iso,
                )
            )
    return rows


def _parse_result_table(html: str) -> list[TFFMatchRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[TFFMatchRow] = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not headers:
            continue
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < 4:
                continue
            home = cells[0].strip()
            away = cells[2].strip() if len(cells) > 2 else ""
            home_goals_raw = cells[1].strip() if len(cells) > 1 else ""
            away_goals_raw = cells[3].strip() if len(cells) > 3 else ""
            date_text = cells[4].strip() if len(cells) > 4 else ""
            time_text = cells[5].strip() if len(cells) > 5 else ""
            if not home or not away:
                continue
            home_goals = _safe_int(home_goals_raw)
            away_goals = _safe_int(away_goals_raw)
            result = _derive_result(home_goals, away_goals)
            kickoff_iso = _try_parse_datetime(date_text, time_text)
            match_id = _slugify(home, away, date_text)
            rows.append(
                TFFMatchRow(
                    match_id=match_id,
                    home_team=home,
                    away_team=away,
                    league="TFF",
                    kickoff_iso=kickoff_iso,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    result=result,
                )
            )
    return rows


def _safe_int(value: str) -> int | None:
    value = value.strip()
    if not value or value == "-":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _derive_result(home_goals: int | None, away_goals: int | None) -> str | None:
    if home_goals is None or away_goals is None:
        return None
    if home_goals > away_goals:
        return "1"
    if home_goals < away_goals:
        return "2"
    return "X"


def _try_parse_datetime(date_text: str, time_text: str) -> str:
    date_text = date_text.strip()
    time_text = time_text.strip()
    if not date_text:
        return datetime.now(timezone.utc).isoformat()
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(f"{date_text} {time_text}".strip(), fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat()


def _slugify(home: str, away: str, date_text: str) -> str:
    raw = f"{home}-{away}-{date_text}"
    raw = re.sub(r"[^a-zA-Z0-9ğüşıöçİĞÜŞİÖÇ]+", "-", raw)
    return re.sub(r"-{2,}", "-", raw).strip("-").lower()


def fetch_fixtures(url: str = FIXTURE_URL) -> list[TFFMatchRow]:
    html = _http_get_text(url)
    return _parse_fixture_table(html)


def fetch_results(url: str = LIVE_URL) -> list[TFFMatchRow]:
    html = _http_get_text(url)
    return _parse_result_table(html)


def append_matches(rows: Sequence[TFFMatchRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                existing.add(record.get("match_id"))
            except json.JSONDecodeError:
                continue
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            if row.match_id in existing:
                continue
            payload = {
                "match_id": row.match_id,
                "home_team": row.home_team,
                "away_team": row.away_team,
                "league": row.league,
                "kickoff_iso": row.kickoff_iso,
                "home_goals": row.home_goals,
                "away_goals": row.away_goals,
                "result": row.result,
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


__all__ = [
    "TFFMatchRow",
    "fetch_fixtures",
    "fetch_results",
    "append_matches",
]
