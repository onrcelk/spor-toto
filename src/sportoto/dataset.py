"""Dataset loaders built on top of masha integration.

Reads from the local raw memory directory instead of hitting the live
page on every run. This keeps analysis stable and offline-reviewable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sportoto.masha_integration import SportotoMatchRow, NewsItem, fetch_sportoto_list, collect_news, append_news, append_sportoto_list


RAW_DIR = Path("~/.sportoto/raw").expanduser()


def ensure_raw_dir() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_DIR


def refresh_sportoto_memory(path: Path | str = RAW_DIR / "sportoto_list_latest.json") -> list[dict[str, Any]]:
    target = Path(path).expanduser()
    rows = fetch_sportoto_list()
    if not rows:
        return []
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({
                "match_index": row.match_index,
                "home_team": row.home_team,
                "away_team": row.away_team,
                "date_text": row.date_text,
                "time_text": row.time_text,
                "source_url": row.source_url,
                "fetched_at": row.fetched_at,
            }, ensure_ascii=False) + "\n")
    return [asdict(row) for row in rows]


def load_latest_matches(path: Path | str = RAW_DIR / "sportoto_list_latest.json") -> list[dict[str, Any]]:
    target = Path(path).expanduser()
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def refresh_news_memory(path: Path | str = RAW_DIR / "news_latest.jsonl", limit: int = 20) -> list[dict[str, Any]]:
    target = Path(path).expanduser()
    items = collect_news(limit=limit)
    if not items:
        return []
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps({
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "source": item.source,
                "published_at": item.published_at,
                "category": item.category,
                "teams": item.teams,
                "league": item.league,
            }, ensure_ascii=False) + "\n")
    return [asdict(item) for item in items]


def load_latest_news(path: Path | str = RAW_DIR / "news_latest.jsonl") -> list[dict[str, Any]]:
    target = Path(path).expanduser()
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def evaluate_next_week() -> dict[str, Any]:
    matches = load_latest_matches()
    news = load_latest_news()
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "match_count": len(matches),
        "news_count": len(news),
        "matches": matches,
        "news": news,
    }


__all__ = [
    "refresh_sportoto_memory",
    "load_latest_matches",
    "refresh_news_memory",
    "load_latest_news",
    "evaluate_next_week",
]
