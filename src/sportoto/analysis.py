"""Match analysis module.

Provides structured analysis for upcoming matches including:
- Feature extraction
- Model prediction
- Confidence scoring
- Comparison with market odds when available
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sportoto.features import MatchFeatures
from sportoto.model import MatchModel, MatchPrediction


@dataclass(frozen=True)
class MatchAnalysis:
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff_iso: str
    prediction: MatchPrediction
    features: MatchFeatures
    notes: list[str]
    analyzed_at: str


def analyze_match(
    match: MatchFeatures,
    model: MatchModel,
    notes: list[str] | None = None,
) -> MatchAnalysis:
    if notes is None:
        notes = []
    prediction = model.predict(match)
    return MatchAnalysis(
        match_id=match.match_id,
        home_team=match.home_team,
        away_team=match.away_team,
        league=match.league,
        kickoff_iso=match.kickoff_iso,
        prediction=prediction,
        features=match,
        notes=notes,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )


def format_analysis(analysis: MatchAnalysis) -> str:
    lines = [
        f"Maç: {analysis.home_team} - {analysis.away_team}",
        f"Lig: {analysis.league}",
        f"Tarih: {analysis.kickoff_iso}",
        f"Tahmin:",
        f"  1: {analysis.prediction.pred_home_win:.2%}",
        f"  X: {analysis.prediction.pred_draw:.2%}",
        f"  2: {analysis.prediction.pred_away_win:.2%}",
        f"  Over 2.5: {analysis.prediction.pred_over_2_5:.2%}",
        f"  Under 2.5: {analysis.prediction.pred_under_2_5:.2%}",
        f"Güven: {analysis.prediction.confidence:.2%}",
    ]
    if analysis.notes:
        lines.append("Notlar:")
        for note in analysis.notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


__all__ = ["MatchAnalysis", "analyze_match", "format_analysis"]
