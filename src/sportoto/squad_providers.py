"""Raw squad providers; providers return claims without interpreting match outcome."""
from __future__ import annotations

from typing import Any, Iterable, Protocol


class SquadProvider(Protocol):
    source: str

    def fetch(self, match_id: str, context: dict[str, Any]) -> list[dict[str, Any]] | None:
        ...


class StaticSquadProvider:
    """Read-only fixture provider for official/news-normalized availability claims."""

    def __init__(self, rows: Iterable[dict[str, Any]], source: str = "static_squad") -> None:
        self.source = source
        self._rows: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            match_id = str(row["match_id"])
            claims = row.get("claims", [])
            self._rows.setdefault(match_id, []).extend(dict(c) for c in claims)

    def fetch(self, match_id: str, context: dict[str, Any]) -> list[dict[str, Any]] | None:
        if str(match_id) not in self._rows:
            return None
        return [dict(claim, source=claim.get("source", self.source)) for claim in self._rows[str(match_id)]]


__all__ = ["SquadProvider", "StaticSquadProvider"]
