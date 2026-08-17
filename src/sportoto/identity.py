"""Provider-independent team identity and alias resolution."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence


# Canonical (Spor Toto / model) name <-> provider name aliases.
# The Odds API uses short forms like "Erzurum BB", "Fenerbahce", "Besiktas JK".
TEAM_ALIASES: dict[str, list[str]] = {
    "Erzurumspor FK": ["erzurum bb", "erzurumspor", "bb erzurumspor"],
    "Galatasaray A.Ş.": ["galatasaray", "galatasaray as"],
    "Fenerbahçe A.Ş.": ["fenerbahce", "fenerbahce as", "fenerbahce jk"],
    "Beşiktaş A.Ş.": ["besiktas", "besiktas jk", "besiktas as"],
    "Trabzonspor A.Ş.": ["trabzonspor"],
    "Başakşehir FK": ["basaksehir", "istanbul basaksehir", "medipol basaksehir"],
    "Gaziantep FK": ["gazisehir gaziantep", "gazişehir gaziantep", "gaziantep"],
    "Konyaspor": ["torku konyaspor", "konyaspor"],
    "Alanyaspor": ["alanyaspor"],
    "Eyüpspor": ["eyupspor"],
    "Samsunspor A.Ş.": ["samsunspor"],
    "Göztepe A.Ş.": ["goztepe"],
    "Çaykur Rizespor A.Ş.": ["caykur rizespor", "rizespor"],
    "Kasımpaşa A.Ş.": ["kasimpasa"],
    "Çorum FK": ["corum", "corum fk"],
    "Kocaelispor": ["kocaelispor"],
    "Gençlerbirliği": ["genclerbirligi"],
    "Amed Sportif": ["amed", "amed sportif"],
}


def normalize_team_name(name: str) -> str:
    value = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"\b(a\.?s\.?|s\.?k\.?|f\.?k\.?|f\.?c\.?|c\.?f\.?|a\.?f\.?c\.?|as|spor kulubu|futbol kulubu|jk)\b", " ", value)
    value = re.sub(r"\.?", "", value)
    return re.sub(r"[^a-z0-9]+", "", value)


# Precomputed alias lookup (normalized alias -> canonical)
_ALIAS_LOOKUP: dict[str, str] = {}
for _canon, _names in TEAM_ALIASES.items():
    _ALIAS_LOOKUP[normalize_team_name(_canon)] = _canon
    for _n in _names:
        _ALIAS_LOOKUP[normalize_team_name(_n)] = _canon


def resolve_team(name: str) -> str:
    """Return canonical team name if known, else the input (normalized-ish)."""
    n = normalize_team_name(name)
    if n in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[n]
    return name


class TeamIdentityResolver:
    def __init__(self, aliases: Mapping[str, Sequence[str]] | None = None) -> None:
        self._lookup: dict[str, str] = {**_ALIAS_LOOKUP}
        for canonical, names in (aliases or {}).items():
            self._lookup[normalize_team_name(canonical)] = canonical
            for name in names:
                self._lookup[normalize_team_name(name)] = canonical

    def resolve(self, provider_name: str) -> str:
        return self._lookup.get(normalize_team_name(provider_name), provider_name)

    def add_alias(self, canonical: str, provider_name: str) -> None:
        self._lookup[normalize_team_name(canonical)] = canonical
        self._lookup[normalize_team_name(provider_name)] = canonical


__all__ = ["TeamIdentityResolver", "normalize_team_name", "resolve_team", "TEAM_ALIASES"]
