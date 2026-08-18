"""Raw news providers; providers return claims, not match predictions."""
from __future__ import annotations

from typing import Any, Iterable, Protocol


class NewsProvider(Protocol):
    source: str

    def fetch(self, match_id: str, context: dict[str, Any]) -> list[dict[str, Any]] | None:
        ...


class StaticNewsProvider:
    def __init__(self, rows: Iterable[dict[str, Any]], source: str = "static_news") -> None:
        self.source = source
        self._rows: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            self._rows.setdefault(str(row["match_id"]), []).extend(dict(c) for c in row.get("claims", []))

    def fetch(self, match_id: str, context: dict[str, Any]) -> list[dict[str, Any]] | None:
        if str(match_id) not in self._rows:
            return None
        return [dict(claim, source=claim.get("source", self.source)) for claim in self._rows[str(match_id)]]


__all__ = ["NewsProvider", "StaticNewsProvider"]
