"""Provider-independent team identity and alias resolution."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence


def normalize_team_name(name: str) -> str:
    value = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"\b(a\.s\.|a s|sk|fk|fc|cf|afc|as|spor kulubu|futbol kulubu)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value)


class TeamIdentityResolver:
    def __init__(self, aliases: Mapping[str, Sequence[str]] | None = None) -> None:
        self._lookup: dict[str, str] = {}
        for canonical, names in (aliases or {}).items():
            self._lookup[normalize_team_name(canonical)] = canonical
            for name in names:
                self._lookup[normalize_team_name(name)] = canonical

    def resolve(self, provider_name: str) -> str:
        return self._lookup.get(normalize_team_name(provider_name), provider_name)

    def add_alias(self, canonical: str, provider_name: str) -> None:
        self._lookup[normalize_team_name(canonical)] = canonical
        self._lookup[normalize_team_name(provider_name)] = canonical


__all__ = ["TeamIdentityResolver", "normalize_team_name"]
