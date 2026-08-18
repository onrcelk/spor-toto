"""Raw odds providers; providers do not normalize or interpret odds."""
from __future__ import annotations

from typing import Any, Iterable, Protocol


class OddsProvider(Protocol):
    source: str

    def fetch(self, match_id: str, context: dict[str, Any]) -> dict[str, Any] | None:
        ...


class TelegramStaticOddsProvider:
    """Read-only provider for normalized rows extracted from a Telegram image."""

    source = "user_telegram_screenshot"

    def __init__(self, rows: Iterable[dict[str, Any]]) -> None:
        self._rows: dict[str, dict[str, Any]] = {}
        self._duplicates: set[str] = set()
        for row in rows:
            key = str(row.get("match_id", row.get("match_index", "")))
            if key in self._rows:
                self._duplicates.add(key)
            self._rows[key] = dict(row)

    def fetch(self, match_id: str, context: dict[str, Any]) -> dict[str, Any] | None:
        row = self._rows.get(str(match_id))
        if row is None:
            return None
        result = dict(row)
        result["provider_duplicate"] = str(match_id) in self._duplicates
        result.setdefault("source", self.source)
        return result


__all__ = ["OddsProvider", "TelegramStaticOddsProvider"]
