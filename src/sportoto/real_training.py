"""Build training records from real historical football results.

Primary bulk source: football-data.co.uk CSV files. Mackolik is used as a
read-only cross-check/source adapter for archived fixture pages.
"""
from __future__ import annotations

import io
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup

FOOTBALL_DATA_URLS = {
    # Current Spor Toto can mix Turkey and major European leagues.
    "turkey-2025-2026": "https://www.football-data.co.uk/mmz4281/2526/T1.csv",
    "turkey-2024-2025": "https://www.football-data.co.uk/mmz4281/2425/T1.csv",
    "england-2025-2026": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "england-2024-2025": "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
    "france-2025-2026": "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    "france-2024-2025": "https://www.football-data.co.uk/mmz4281/2425/F1.csv",
    "spain-2025-2026": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "spain-2024-2025": "https://www.football-data.co.uk/mmz4281/2425/SP1.csv",
}

@dataclass(frozen=True)
class HistoricalMatch:
    date: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    source: str
    competition: str = "Unknown"


def fetch_football_data(seasons: Iterable[str] = FOOTBALL_DATA_URLS) -> list[HistoricalMatch]:
    rows: list[HistoricalMatch] = []
    for season in seasons:
        url = FOOTBALL_DATA_URLS[season] if season in FOOTBALL_DATA_URLS else season
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        frame = pd.read_csv(io.BytesIO(response.content), encoding="latin1")
        needed = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}
        if not needed.issubset(frame.columns):
            continue
        for item in frame.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"]).to_dict("records"):
            competition = season.split("-")[0].replace("turkey", "Turkey")
            if "england" in season:
                competition = "England Premier League"
            elif "france" in season:
                competition = "France Ligue 1"
            elif "spain" in season:
                competition = "Spain La Liga"
            else:
                competition = "Turkey Super Lig"
            rows.append(HistoricalMatch(str(item["Date"]), str(item["HomeTeam"]), str(item["AwayTeam"]), int(item["FTHG"]), int(item["FTAG"]), "football-data.co.uk", competition))
    return rows


def parse_mackolik_archive(html: str) -> list[HistoricalMatch]:
    """Parse archived Mackolik fixture text/HTML where scores are links."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    # The archive exposes repeated date, home, score, away blocks; parse the
    # stable score-link sequence and surrounding team links.
    result: list[HistoricalMatch] = []
    for link in soup.find_all("a", href=re.compile(r"/mac/")):
        score = link.get_text(" ", strip=True)
        if not re.fullmatch(r"\d+", score):
            continue
        parent = link.parent.parent if link.parent else None
        if not parent:
            continue
        team_links = [a.get_text(" ", strip=True) for a in parent.find_all("a", href=re.compile(r"/takim/"))]
        if len(team_links) >= 2:
            result.append(HistoricalMatch("", team_links[0], team_links[1], int(score), 0, "mackolik", "Mackolik archive"))
    return result


def build_training_frame(matches: list[HistoricalMatch]) -> pd.DataFrame:
    history: dict[str, deque[tuple[int, int, int]]] = defaultdict(lambda: deque(maxlen=5))
    records: list[dict] = []
    for index, match in enumerate(matches):
        home = history[match.home_team]
        away = history[match.away_team]
        def avg(team: deque[tuple[int, int, int]], pos: int) -> float:
            return sum(x[pos] for x in team) / len(team) if team else 1.2
        home_points = sum(x[2] for x in home) / len(home) if home else 1.0
        away_points = sum(x[2] for x in away) / len(away) if away else 1.0
        records.append({
            "match_id": f"REAL-{index+1}", "home_team": match.home_team, "away_team": match.away_team,
            "league": match.competition, "kickoff_iso": match.date,
            "home_goals_avg": avg(home, 0), "away_goals_avg": avg(away, 0),
            "home_conceded_avg": avg(home, 1), "away_conceded_avg": avg(away, 1),
            "home_form_points": home_points, "away_form_points": away_points,
            "h2h_home_win_rate": 0.5, "h2h_draw_rate": 0.25, "h2h_away_win_rate": 0.25,
            "home_xg_avg": avg(home, 0), "away_xg_avg": avg(away, 0), "is_derby": False,
            "rest_days_home": 7, "rest_days_away": 7,
            "actual_1x2": 0 if match.home_goals > match.away_goals else (2 if match.home_goals < match.away_goals else 1),
            "actual_ou": int(match.home_goals + match.away_goals > 2.5),
        })
        home.append((match.home_goals, match.away_goals, 3 if match.home_goals > match.away_goals else (1 if match.home_goals == match.away_goals else 0)))
        away.append((match.away_goals, match.home_goals, 3 if match.away_goals > match.home_goals else (1 if match.home_goals == match.away_goals else 0)))
    return pd.DataFrame(records)


def train_from_real_data(output_frame: Path, model_path: Path) -> tuple[int, object]:
    from .real_training import build_training_frame, fetch_football_data
    from .train import load_records_from_store, train_model
    frame = build_training_frame(fetch_football_data())
    frame.to_parquet(output_frame, index=False)
    return len(frame), train_model(load_records_from_store(output_frame), model_path)
