"""Live / closing odds adapter (read-only).

NOTE ON FREE-TIER LIMITS (verified 2026-08-17):
- API-Sports Free plan does NOT grant access to the /odds endpoint
  (error: "Free plans do not have access to this date"). The odds adapter
  therefore supports an injected JSON fixture / local cache so the pipeline
  can be developed and tested without a paid key. When a paid key is present,
  set SPOROTO_ODDS_SOURCE=api-sports and the live fetch path activates.

This module converts raw odds into model-vs-market comparison inputs:
- implied probabilities (vig-removed)
- EV (edge) for each pick
- closing-line delta (opening vs closing)

All functions are pure / side-effect free except fetch_api_sports_odds.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .market import closing_line_delta, remove_vig
from .identity import normalize_team_name

JsonOpener = Callable[[urllib.request.Request], dict[str, Any]]


@dataclass(frozen=True)
class MatchOdds:
    source: str
    home_team: str
    away_team: str
    bookmaker: str
    opening_1x2: dict[str, float]  # {"1":, "X":, "2":}
    closing_1x2: dict[str, float]
    opening_ou: dict[str, float] | None  # {"over":, "under":} decimal odds
    closing_ou: dict[str, float] | None
    fetched_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_opener(request: urllib.request.Request) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def fetch_api_sports_odds(date: str, api_key: str | None = None,
                          base_url: str | None = None,
                          opener: JsonOpener | None = None) -> list[MatchOdds]:
    """Fetch 1X2 + O/U odds for a date from API-Sports.

    Raises if no key or if the plan does not include odds (Free plan).
    """
    key = api_key or os.getenv("API_SPORTS_KEY", "")
    if not key:
        raise ValueError("API_SPORTS_KEY is required for odds")
    base = (base_url or os.getenv("API_SPORTS_BASE_URL", "https://v3.football.api-sports.io")).rstrip("/")
    url = f"{base}/odds?{urllib.parse.urlencode({'date': date})}"
    payload = _request_json(url, {"x-apisports-key": key, "Accept": "application/json"}, opener)
    return [_parse_api_sports_item(item) for item in payload.get("response", [])]


def _request_json(url, headers, opener):
    return (opener or _default_opener)(urllib.request.Request(url, headers=headers))


def _parse_api_sports_item(item: dict) -> MatchOdds:
    teams = item.get("teams", {})
    home = teams.get("home", {}).get("name", "")
    away = teams.get("away", {}).get("name", "")
    bookmakers = item.get("bookmakers", [])
    # pick the first bookmaker that carries 1X2 + O/U
    for bm in bookmakers:
        one_x_two = None
        ou = None
        for bet in bm.get("bets", []):
            if bet.get("label") == "1X2":
                one_x_two = {v["value"]: float(v["odd"]) for v in bet.get("values", [])}
            elif bet.get("label") == "Over/Under":
                for v in bet.get("values", []):
                    if v["value"].startswith("Over"):
                        ou = {"over": float(v["odd"]), "under": None}
                    elif v["value"].startswith("Under") and ou is not None:
                        ou["under"] = float(v["odd"])
        if one_x_two and len(one_x_two) == 3:
            # API-Sports returns a single snapshot; treat it as both opening & closing
            return MatchOdds(
                source="api-sports", home_team=home, away_team=away,
                bookmaker=bm.get("name", "unknown"),
                opening_1x2=one_x_two, closing_1x2=dict(one_x_two),
                opening_ou=ou, closing_ou=ou, fetched_at=_now(),
            )
    # fallback: empty odds
    return MatchOdds(source="api-sports", home_team=home, away_team=away,
                     bookmaker="none", opening_1x2={}, closing_1x2={},
                     opening_ou=None, closing_ou=None, fetched_at=_now())


def load_local_odds(path: str) -> list[MatchOdds]:
    """Load odds from a local JSON file (cache / fixture) for testing."""
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("odds", [])
    out = []
    for r in rows:
        out.append(MatchOdds(
            source=r.get("source", "local"),
            home_team=r["home_team"], away_team=r["away_team"],
            bookmaker=r.get("bookmaker", "local"),
            opening_1x2=r.get("opening_1x2", {}), closing_1x2=r.get("closing_1x2", r.get("opening_1x2", {})),
            opening_ou=r.get("opening_ou"), closing_ou=r.get("closing_ou", r.get("opening_ou")),
            fetched_at=r.get("fetched_at", _now()),
        ))
    return out


def market_vs_model(odds: list[MatchOdds], predictions: list[dict]) -> list[dict]:
    """Join real odds with model predictions and compute EV + closing-line delta."""
    pred_by_team = {}
    for p in predictions:
        nh = normalize_team_name(p["home_team"])
        na = normalize_team_name(p["away_team"])
        pred_by_team[(nh, na)] = p

    out = []
    for o in odds:
        key = (normalize_team_name(o.home_team), normalize_team_name(o.away_team))
        pred = pred_by_team.get(key)
        if not pred:
            continue
        pick = pred.get("predicted_1x2")
        closing = o.closing_1x2 or o.opening_1x2
        implied = remove_vig(closing) if closing else {}
        # probability the model assigns to the pick
        model_p = None
        if pick == "1":
            model_p = pred.get("pred_home_win")
        elif pick == "X":
            model_p = pred.get("pred_draw")
        elif pick == "2":
            model_p = pred.get("pred_away_win")
        pick_odds = closing.get(pick) if closing else None
        ev = compute_ev_safe(model_p, pick_odds)
        cld = None
        if o.opening_1x2 and o.closing_1x2:
            cld = closing_line_delta(o.opening_1x2, o.closing_1x2)
        out.append({
            "home_team": o.home_team, "away_team": o.away_team,
            "predicted_1x2": pick, "model_prob": model_p,
            "market_implied_prob": implied.get(pick) if implied else None,
            "odds": pick_odds, "ev": ev,
            "closing_line_delta": cld,
            "bookmaker": o.bookmaker, "source": o.source,
        })
    return out


def compute_ev_safe(model_prob, decimal_odds):
    if model_prob is None or decimal_odds is None:
        return None
    try:
        return round(model_prob * float(decimal_odds) - 1.0, 4)
    except Exception:
        return None


__all__ = ["MatchOdds", "fetch_api_sports_odds", "load_local_odds", "market_vs_model"]
