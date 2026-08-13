"""Transfermarkt-backed transfer and manager-change signal integration.

Reads public transfer news, market value updates, and manager-change
signals from Transfermarkt and stores them as structured JSONL records.
Read-only; no posting/subscriptions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.transfermarkt.com"
NEWS_URL = f"{BASE_URL}/news"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass(frozen=True)
class TransferSignal:
    team: str
    signal_type: str  # "transfer" or "manager_change"
    title: str
    url: str
    published_iso: str
    source: str = "transfermarkt"


def _http_get_text(url: str, *, timeout: int = 30) -> str:
    try:
        response = requests.get(url, timeout=timeout, headers=HEADERS, verify=False)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"Transfermarkt verisi çekilemedi: {url} ({exc})") from exc


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_news_items(html: str) -> list[TransferSignal]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[TransferSignal] = []
    seen: set[str] = set()
    for article in soup.find_all(["article", "div", "li"], class_=re.compile(r"news|article|teaser", re.I)):
        title_tag = article.find(["h2", "h3", "a"], class_=re.compile(r"title|headline", re.I))
        if not title_tag:
            continue
        title = _clean(title_tag.get_text())
        link_tag = title_tag if title_tag.name == "a" else article.find("a", href=True)
        if not link_tag or not link_tag.get("href"):
            continue
        href = link_tag["href"]
        if href.startswith("/"):
            href = BASE_URL + href
        time_tag = article.find(["time", "span"], class_=re.compile(r"date|time", re.I))
        published_iso = "2026-01-01T00:00:00+00:00"
        if time_tag and time_tag.get("datetime"):
            published_iso = time_tag["datetime"]
        elif time_tag:
            published_iso = _clean(time_tag.get_text())

        signal_type = "transfer"
        text_blob = _clean(article.get_text()).lower()
        if any(keyword in text_blob for keyword in ["antrenör", "teknik direktör", "manager", "coach", " appointed", "resigned"]):
            signal_type = "manager_change"

        team_match = re.search(r"^([A-Za-zğüşıöçİĞÜŞİÖÇ\s\.\-]+?)(?:\s*[:\-]\s*|$)", title)
        team = team_match.group(1).strip() if team_match else "Unknown"
        if team not in seen:
            seen.add(team)
            items.append(TransferSignal(team=team, signal_type=signal_type, title=title, url=href, published_iso=published_iso))
    return items


def fetch_transfer_signals(url: str = NEWS_URL) -> list[TransferSignal]:
    html = _http_get_text(url)
    return _extract_news_items(html)


def append_signals(signals: Sequence[TransferSignal], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_urls: set[str] = set()
    existing_team_title: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                existing_urls.add(record.get("url"))
                existing_team_title.add((record.get("team"), record.get("title")))
            except json.JSONDecodeError:
                continue
    with path.open("a", encoding="utf-8") as fh:
        for signal in signals:
            if signal.url in existing_urls or (signal.team, signal.title) in existing_team_title:
                continue
            payload = {
                "team": signal.team,
                "signal_type": signal.signal_type,
                "title": signal.title,
                "url": signal.url,
                "published_iso": signal.published_iso,
                "source": signal.source,
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


__all__ = [
    "TransferSignal",
    "fetch_transfer_signals",
    "append_signals",
]
