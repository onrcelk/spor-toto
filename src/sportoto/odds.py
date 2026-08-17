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
from .identity import normalize_team_name, resolve_team

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


_FDCOUK_BASE = "https://www.football-data.co.uk/mmz4281"


def fetch_fdccouk(season: str = "2324", league: str = "T1",
                  bookmaker: str = "B365") -> list[MatchOdds]:
    """Fetch real closing 1X2 + O/U odds from football-data.co.uk (FREE, no key).

    season: "2324" (2023-24), "2223", ...  league: "T1"=Turkey SL,
    "E0"=EPL, "SP1"=La Liga, "D1"=Bundesliga, "I1"=Serie A, "F1"=Ligue1.
    bookmaker: column prefix ("B365", "PS", "WH", "VCH", "Avg"...).
    The site publishes end-of-day (closing) odds per match; we treat them as
    both opening & closing (single snapshot). O/U columns are "<bm>>2.5"/"<bm><2.5".
    """
    url = f"{_FDCOUK_BASE}/{season}/{league}.csv"
    import csv, io
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")
    reader = csv.DictReader(io.StringIO(text))
    h_col, d_col, a_col = f"{bookmaker}H", f"{bookmaker}D", f"{bookmaker}A"
    ou_over, ou_under = f"{bookmaker}>2.5", f"{bookmaker}<2.5"
    out = []
    for row in reader:
        try:
            h = float(row.get(h_col) or row.get("AvgH"))
            d = float(row.get(d_col) or row.get("AvgD"))
            a = float(row.get(a_col) or row.get("AvgA"))
        except (TypeError, ValueError):
            continue
        one_x_two = {"1": h, "X": d, "2": a}
        ou = None
        try:
            ou = {"over": float(row[ou_over]), "under": float(row[ou_under])}
        except (KeyError, TypeError, ValueError):
            ou = None
        out.append(MatchOdds(
            source="football-data.co.uk", home_team=row.get("HomeTeam", ""),
            away_team=row.get("AwayTeam", ""), bookmaker=bookmaker,
            opening_1x2=one_x_two, closing_1x2=dict(one_x_two),
            opening_ou=ou, closing_ou=ou, fetched_at=_now(),
        ))
    return out


# The Odds API (https://the-odds-api.com) — FREE tier 500 credits/month, no card.
# Covers soccer_turkey_super_league + all major leagues. Requires API key.
_THEODDS_BASE = "https://api.the-odds-api.com/v4"


def fetch_theodds(sport: str = "soccer_turkey_super_league", api_key: str | None = None,
                  regions: str = "eu", bookmaker: str | None = None) -> list[MatchOdds]:
    """Fetch LIVE 1X2 + O/U odds from The Odds API (free 500 credits/mo).

    sport: e.g. soccer_turkey_super_league, soccer_epl, soccer_spain_la_liga.
    Returns opening_1x2=first snapshot, closing_1x2=latest (we keep the last
    bookmaker's h2h as the working line; for multi-bookmaker CLV use oddsformat).
    """
    key = api_key or os.getenv("THE_ODDS_API_KEY", "")
    if not key:
        raise ValueError("THE_ODDS_API_KEY required (free tier: the-odds-api.com)")
    params = urllib.parse.urlencode({
        "apiKey": key, "regions": regions,
        "markets": "h2h,totals", "oddsFormat": "decimal",
    })
    if bookmaker:
        params += f"&bookmakers={bookmaker}"
    url = f"{_THEODDS_BASE}/sports/{sport}/odds?{params}"
    data = _request_json(url, {"Accept": "application/json"}, None)
    out = []
    for ev in data:
        home = ev.get("home_team", "")
        away = ev.get("away_team", "")
        # h2h ve totals ayrı bookmaker'larda olabilir; tümünü tara
        bms = ev.get("bookmakers", [])
        if not bms:
            continue
        one_x_two = None
        ou = None
        for bm in bms:
            for mkt in bm.get("markets", []):
                if mkt.get("key") == "h2h" and one_x_two is None:
                    one_x_two = {_outcome_key(o["name"], home, away): float(o["price"])
                                 for o in mkt.get("outcomes", [])}
                elif mkt.get("key") == "totals" and ou is None:
                    for o in mkt.get("outcomes", []):
                        nm = o["name"].lower()
                        if nm.startswith("over"):
                            ou = {"over": float(o["price"]), "under": None}
                        elif nm.startswith("under") and ou is not None:
                            ou["under"] = float(o["price"])
            if one_x_two and ou:
                break
        if one_x_two and len(one_x_two) == 3:
            out.append(MatchOdds(
                source="the-odds-api", home_team=home, away_team=away,
                bookmaker=bms[0].get("title", bms[0].get("key", "unknown")),
                opening_1x2=one_x_two, closing_1x2=dict(one_x_two),
                opening_ou=ou, closing_ou=ou, fetched_at=_now(),
            ))
    return out


def _outcome_key(name: str, home: str, away: str) -> str:
    nl = name.lower()
    if nl == home.lower():
        return "1"
    if nl == away.lower():
        return "2"
    return "X"  # "Draw" / "Berabere"


def market_vs_model(odds: list[MatchOdds], predictions: list[dict]) -> list[dict]:
    """Join real odds with model predictions and compute EV + closing-line delta."""
    pred_by_team = {}
    for p in predictions:
        nh = resolve_team(p["home_team"])
        na = resolve_team(p["away_team"])
        pred_by_team[(nh, na)] = p

    out = []
    for o in odds:
        key = (resolve_team(o.home_team), resolve_team(o.away_team))
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


def fetch_fdccouk_results(season: str = "2324", league: str = "T1") -> list[dict]:
    """Fetch REAL final scores from football-data.co.uk (FREE, no key).

    Returns rows compatible with audit._match_real: {home_team, away_team,
    home_goals, away_goals, source}. Used as an independent results source for
    the audit module (proves hit/miss without paid APIs).
    """
    url = f"{_FDCOUK_BASE}/{season}/{league}.csv"
    import csv, io
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for row in reader:
        try:
            hg = int(row.get("FTHG"))
            ag = int(row.get("FTAG"))
        except (TypeError, ValueError):
            continue
        out.append({
            "home_team": row.get("HomeTeam", ""), "away_team": row.get("AwayTeam", ""),
            "home_goals": hg, "away_goals": ag, "source": "football-data.co.uk",
        })
    return out


__all__ = ["MatchOdds", "fetch_api_sports_odds", "load_local_odds", "market_vs_model",
           "fetch_fdccouk", "fetch_theodds", "fetch_fdccouk_results", "fetch_betbetter"]


# Bet Better (https://betbetter.world/api/) — FREE, NO KEY, CC BY 4.0.
# Independent model win-probabilities + fair odds across 9 sports. Soccer:
# /soccer/{league}/  (EPL, La Liga, Serie A, Bundesliga, Ligue 1, MLS, World Cup).
# Used as a CROSS-CHECK source for our own model (independent probability),
# NOT as the primary odds feed. Active mainly during the soccer season.
_BETBETTER_BASE = "https://betbetter.world"


def fetch_betbetter(league: str = "epl") -> list[MatchOdds]:
    """Fetch Bet Better model probabilities + fair odds for a soccer league.

    Returns MatchOdds where closing_1x2 = Bet Better's fair odds (no bookmaker
    margin) and an extra ``model_prob`` is NOT stored here — callers should use
    market_vs_model with our own predictions; Bet Better is the independent ref.
    """
    hdr = {"User-Agent": "Mozilla/5.0 (compatible; SportotoBot/1.0)"}
    url = f"{_BETBETTER_BASE}/soccer/{league}/"
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=25) as resp:
        html = resp.read().decode("utf-8", "replace")
    # Bet Better renders matchup links like /soccer/epl/matchups/team-a-vs-team-b
    import re
    matchups = re.findall(r'href="(/soccer/[a-z0-9]+/matchups/[^"]+)"', html)
    out = []
    for m in matchups:
        # team-a-vs-team-b -> parse probabilities from the matchup page JSON
        try:
            murl = f"{_BETBETTER_BASE}{m}"
            mreq = urllib.request.Request(murl, headers=hdr)
            mhtml = urllib.request.urlopen(mreq, timeout=25).read().decode("utf-8", "replace")
            # look for embedded JSON with probabilities (best-effort)
            js = re.search(r'\{[^{}]*"home"[^}]*"away"[^}]*\}', mhtml)
            if not js:
                continue
            data = json.loads(js.group(0))
            home = data.get("home", {}).get("name", "")
            away = data.get("away", {}).get("name", "")
            ph = float(data.get("home", {}).get("prob", 0.33))
            pa = float(data.get("away", {}).get("prob", 0.33))
            pd = max(0.01, 1 - ph - pa)
            # fair odds = 1/prob (no margin)
            out.append(MatchOdds(
                source="betbetter", home_team=home, away_team=away,
                bookmaker="betbetter-model",
                opening_1x2={"1": round(1/ph, 2), "X": round(1/pd, 2), "2": round(1/pa, 2)},
                closing_1x2={"1": round(1/ph, 2), "X": round(1/pd, 2), "2": round(1/pa, 2)},
                opening_ou=None, closing_ou=None, fetched_at=_now(),
            ))
        except Exception:
            continue
    return out
