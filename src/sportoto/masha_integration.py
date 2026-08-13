"""Masha-backed external data integration.

This module pulls match schedules, transfer news, and manager-change
signals from the web and stores them as structured JSONL records.
Read-only; no posting or automated publishing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_NEWS_QUERIES = [
    "Spor Toto Süper Lig haftanın maçları",
    "Süper Lig transfer haberleri",
    "Süper Lig teknik direktör değişikliği",
]

_SPOR_TOTO_LIST_URL = "https://www.sportoto.gov.tr/spor-toto-listeler"


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    snippet: str
    source: str
    published_at: str
    category: str
    teams: list[str]
    league: str = "Süper Lig"


@dataclass(frozen=True)
class SportotoMatchRow:
    match_index: int
    home_team: str
    away_team: str
    date_text: str
    time_text: str
    source_url: str
    fetched_at: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get_text(url: str, timeout: int = 20) -> str:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("requests is required for masha integration") from exc
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    payload = _http_get_text(f"https://html.duckduckgo.com/html/?q={query}")
    results: list[dict[str, Any]] = []
    for line in payload.splitlines():
        line = line.strip()
        if "href=" not in line:
            continue
        if 'class="result__a"' in line:
            title = line.split(">", 1)[-1].split("<", 1)[0].strip()
            url = line.split('href="', 1)[-1].split('"', 1)[0]
            results.append({"title": title, "url": url, "snippet": ""})
        if 'class="result__snippet"' in line:
            snippet = line.split(">", 1)[-1].split("<", 1)[0].strip()
            if results:
                results[-1]["snippet"] = snippet
        if len(results) >= limit:
            break
    return results


def _parse_match_line(match_part: str) -> tuple[str, str] | None:
    if " - " not in match_part:
        return None
    home, away = match_part.split(" - ", 1)
    home = home.strip()
    away = away.strip()
    if not home or not away:
        return None
    return home, away


def _parse_browser_text_to_rows(text: str) -> list[SportotoMatchRow]:
    rows: list[SportotoMatchRow] = []
    seen_matches: set[str] = set()
    current: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current.get("match") and current.get("date") and current.get("time"):
                parsed = _parse_match_line(current["match"])
                if parsed:
                    home_team, away_team = parsed
                    key = f"{home_team}|{away_team}|{current['date']}|{current['time']}"
                    if key not in seen_matches:
                        seen_matches.add(key)
                        rows.append(
                            SportotoMatchRow(
                                match_index=len(rows) + 1,
                                home_team=home_team,
                                away_team=away_team,
                                date_text=current["date"],
                                time_text=current["time"],
                                source_url=_SPOR_TOTO_LIST_URL,
                                fetched_at=_utc_now_iso(),
                            )
                        )
            current = {}
            continue
        if " - " in line and not current.get("match"):
            current["match"] = line
        elif any(day in line for day in ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]):
            if current.get("date") and " " not in current["date"]:
                current["date"] = f"{current['date']} {line}"
            else:
                current["date"] = line
        elif ":" in line and len(line) <= 8 and not current.get("time"):
            current["time"] = line
        elif not current.get("date") and line and "/" in line:
            current["date"] = line
    if current.get("match") and current.get("date") and current.get("time"):
        parsed = _parse_match_line(current["match"])
        if parsed:
            home_team, away_team = parsed
            key = f"{home_team}|{away_team}|{current['date']}|{current['time']}"
            if key not in seen_matches:
                seen_matches.add(key)
                rows.append(
                    SportotoMatchRow(
                        match_index=len(rows) + 1,
                        home_team=home_team,
                        away_team=away_team,
                        date_text=current["date"],
                        time_text=current["time"],
                        source_url=_SPOR_TOTO_LIST_URL,
                        fetched_at=_utc_now_iso(),
                    )
                )
    return rows


def _parse_response_text_to_rows(text: str) -> list[SportotoMatchRow]:
    rows: list[SportotoMatchRow] = []
    seen_matches: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or " - " not in line:
            continue
        if line.startswith("|") and all(part.strip().replace("-", "").strip() == "" for part in line.split("|") if part.strip()):
            continue
        if line.lower().startswith("liste ") or "sezonu" in line.lower():
            continue
        parts = [part.strip() for part in line.split("|")]
        match_part = next((p for p in parts if " - " in p), None)
        if not match_part:
            continue
        parsed = _parse_match_line(match_part)
        if parsed is None:
            continue
        home_team, away_team = parsed
        date_part = next((p for p in parts if any(day in p for day in ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"])), "")
        time_part = next((p for p in parts if ":" in p and len(p) <= 8), "")
        key = f"{home_team}|{away_team}|{date_part}|{time_part}"
        if key in seen_matches:
            continue
        seen_matches.add(key)
        rows.append(
            SportotoMatchRow(
                match_index=len(rows) + 1,
                home_team=home_team,
                away_team=away_team,
                date_text=date_part,
                time_text=time_part,
                source_url=_SPOR_TOTO_LIST_URL,
                fetched_at=_utc_now_iso(),
            )
        )
    return rows


def fetch_sportoto_list(url: str = _SPOR_TOTO_LIST_URL) -> list[SportotoMatchRow]:
    # Try browser-backed fetch first for JS-rendered content.
    try:
        from browser_exec import browser_exec
        result = browser_exec(code=f"goto_url('{url}')\nwait_for_load()\ntext = js('document.body.innerText')\nprint(text)")
        text = result.get("output", "")
        if text and ("Galatasaray" in text or "Fenerbahçe" in text):
            return _parse_browser_text_to_rows(text)
    except Exception:
        pass
    # Fallback to direct HTTP.
    text = _http_get_text(url)
    return _parse_response_text_to_rows(text)


def collect_news(queries: list[str] | None = None, limit: int = 10) -> list[NewsItem]:
    if queries is None:
        queries = DEFAULT_NEWS_QUERIES
    seen_urls: set[str] = set()
    items: list[NewsItem] = []
    for query in queries:
        try:
            results = _search(query, limit=limit)
        except RuntimeError:
            continue
        for result in results:
            url = result.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            items.append(
                NewsItem(
                    title=result.get("title", ""),
                    url=url,
                    snippet=result.get("snippet", ""),
                    source=url.split("/")[2] if "/" in url else url,
                    published_at=_utc_now_iso(),
                    category="news",
                    teams=[],
                    league="Süper Lig",
                )
            )
    return items


def append_news(path: Path | str, items: list[NewsItem]) -> int:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
    return len(items)


def append_sportoto_list(path: Path | str, rows: list[SportotoMatchRow]) -> int:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
    return len(rows)


__all__ = ["collect_news", "append_news", "NewsItem", "fetch_sportoto_list", "append_sportoto_list", "SportotoMatchRow"]
