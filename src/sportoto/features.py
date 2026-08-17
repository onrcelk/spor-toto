from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MatchFeatures:
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff_iso: str
    home_goals_avg: float = 0.0
    away_goals_avg: float = 0.0
    home_conceded_avg: float = 0.0
    away_conceded_avg: float = 0.0
    home_form_points: float = 0.0
    away_form_points: float = 0.0
    h2h_home_win_rate: float = 0.5
    h2h_draw_rate: float = 0.25
    h2h_away_win_rate: float = 0.25
    home_xg_avg: float = 0.0
    away_xg_avg: float = 0.0
    is_derby: bool = False
    rest_days_home: int = 7
    rest_days_away: int = 7
    elo_diff: float = 0.0

    def to_vector(self) -> list[float]:
        return [
            self.home_goals_avg,
            self.away_goals_avg,
            self.home_conceded_avg,
            self.away_conceded_avg,
            self.home_form_points,
            self.away_form_points,
            self.h2h_home_win_rate,
            self.h2h_draw_rate,
            self.h2h_away_win_rate,
            self.home_xg_avg,
            self.away_xg_avg,
            float(self.is_derby),
            float(self.rest_days_home),
            float(self.rest_days_away),
            float(self.elo_diff),
        ]

    @staticmethod
    def field_names() -> list[str]:
        return [
            "home_goals_avg",
            "away_goals_avg",
            "home_conceded_avg",
            "away_conceded_avg",
            "home_form_points",
            "away_form_points",
            "h2h_home_win_rate",
            "h2h_draw_rate",
            "h2h_away_win_rate",
            "home_xg_avg",
            "away_xg_avg",
            "is_derby",
            "rest_days_home",
            "rest_days_away",
            "elo_diff",
        ]


__all__ = ["MatchFeatures"]
