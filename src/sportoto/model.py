from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import MatchFeatures


@dataclass(frozen=True)
class MatchPrediction:
    match_id: str
    pred_home_win: float
    pred_draw: float
    pred_away_win: float
    pred_over_2_5: float
    pred_under_2_5: float
    confidence: float
    created_at: str
    predicted_1x2: str | None = None
    predicted_ou: str | None = None


class MatchModel:
    def __init__(self, model_path: Path | str | None = None) -> None:
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    GradientBoostingClassifier(
                        loss="log_loss",
                        n_estimators=180,
                        max_depth=3,
                        learning_rate=0.05,
                        random_state=42,
                    ),
                ),
            ]
        )
        self.classes_: np.ndarray | None = None
        self.fitted: bool = False
        if model_path:
            self.load(Path(model_path))

    def fit(self, features: list[list[float]], labels_1x2: list[int], labels_ou: list[int]) -> None:
        x = np.asarray(features, dtype=float)
        y1 = np.asarray(labels_1x2, dtype=int)
        you = np.asarray(labels_ou, dtype=int)
        self.pipeline.fit(x, y1)
        self.classes_ = self.pipeline.named_steps["clf"].classes_
        self.fitted = True

    def predict(self, match: MatchFeatures) -> MatchPrediction:
        if not self.fitted:
            raise RuntimeError("model is not fitted")
        x = np.asarray([match.to_vector()], dtype=float)
        probs = self.pipeline.predict_proba(x)[0]
        if self.classes_ is None or len(self.classes_) < 3:
            raise RuntimeError("model is missing 1X2 classes")
        home = float(probs[self.classes_ == 0][0]) if np.any(self.classes_ == 0) else 0.0
        draw = float(probs[self.classes_ == 1][0]) if np.any(self.classes_ == 1) else 0.0
        away = float(probs[self.classes_ == 2][0]) if np.any(self.classes_ == 2) else 0.0
        total_expected = match.home_goals_avg + match.away_goals_avg
        over = float(np.clip(total_expected / 5.0, 0.05, 0.95))
        under = 1.0 - over
        confidence = float(np.clip(max(home, draw, away), 0.0, 1.0))
        predicted_1x2 = '1'
        if draw > home and draw > away:
            predicted_1x2 = 'X'
        elif away > home and away > draw:
            predicted_1x2 = '2'
        predicted_ou = 'over' if over >= 0.5 else 'under'
        return MatchPrediction(
            match_id=match.match_id,
            pred_home_win=home,
            pred_draw=draw,
            pred_away_win=away,
            pred_over_2_5=over,
            pred_under_2_5=under,
            confidence=confidence,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            predicted_1x2=predicted_1x2,
            predicted_ou=predicted_ou,
        )

    def save(self, path: Path | str) -> None:
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, str(Path(path).expanduser()))

    def load(self, path: Path | str) -> None:
        self.pipeline = joblib.load(str(Path(path).expanduser()))
        self.fitted = True
