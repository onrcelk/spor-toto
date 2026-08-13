from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .features import MatchFeatures


PREDICTION_COLUMNS = [
    "match_id",
    "home_team",
    "away_team",
    "league",
    "kickoff_iso",
    "pred_home_win",
    "pred_draw",
    "pred_away_win",
    "pred_over_2_5",
    "pred_under_2_5",
    "confidence",
    "created_at",
]


class PredictionStore:
    def __init__(self, path: Path | str = Path("~/.sportoto/predictions.parquet").expanduser()) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self._frame = pd.read_parquet(self.path)
        else:
            self._frame = pd.DataFrame(columns=PREDICTION_COLUMNS)

    def append(self, record: dict[str, Any]) -> None:
        if "match_id" not in record:
            raise ValueError("record must contain match_id")
        self._frame = pd.concat([self._frame, pd.DataFrame([record])], ignore_index=True)
        self._frame.to_parquet(self.path, index=False)

    def latest(self) -> pd.DataFrame:
        return self._frame.copy()

    def by_match(self, match_id: str) -> pd.DataFrame:
        return self._frame[self._frame["match_id"] == match_id].copy()
