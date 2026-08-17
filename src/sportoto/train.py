"""Model training pipeline.

Provides:
- Historical match loader from prediction store / JSONL
- Synthetic data generator for training tests
- Train/save/load workflow for MatchModel
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .features import MatchFeatures
from .model import MatchModel


@dataclass(frozen=True)
class TrainRecord:
    match_id: str
    features: list[float]
    label_1x2: int
    label_ou: int


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_records_from_store(store_path: Path | str = Path("~/.sportoto/predictions.parquet").expanduser()) -> list[TrainRecord]:
    path = Path(store_path).expanduser()
    if not path.exists():
        return []
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for training pipeline") from exc
    frame = pd.read_parquet(path)
    records: list[TrainRecord] = []
    for row in frame.to_dict("records"):
        try:
            record = TrainRecord(
                match_id=str(row.get("match_id", "")),
                features=[
                    float(row.get("home_goals_avg", 0.0)),
                    float(row.get("away_goals_avg", 0.0)),
                    float(row.get("home_conceded_avg", 0.0)),
                    float(row.get("away_conceded_avg", 0.0)),
                    float(row.get("home_form_points", 0.0)),
                    float(row.get("away_form_points", 0.0)),
                    float(row.get("h2h_home_win_rate", 0.5)),
                    float(row.get("h2h_draw_rate", 0.25)),
                    float(row.get("h2h_away_win_rate", 0.25)),
                    float(row.get("home_xg_avg", 0.0)),
                    float(row.get("away_xg_avg", 0.0)),
                    float(row.get("is_derby", False)),
                    float(row.get("rest_days_home", 7)),
                    float(row.get("rest_days_away", 7)),
                    float(row.get("elo_diff", 0.0)),
                ],
                label_1x2=int(row.get("actual_1x2", 0)),
                label_ou=int(row.get("actual_ou", 0)),
            )
            records.append(record)
        except (TypeError, ValueError):
            continue
    return records


def generate_synthetic_training_records(count: int = 120) -> list[TrainRecord]:
    import random

    random.seed(42)
    records: list[TrainRecord] = []
    for i in range(count):
        home_goals_avg = round(random.uniform(0.8, 2.2), 2)
        away_goals_avg = round(random.uniform(0.8, 2.2), 2)
        home_form = round(random.uniform(0, 10), 2)
        away_form = round(random.uniform(0, 10), 2)
        h2h_home = round(random.uniform(0.1, 0.9), 2)
        h2h_draw = round(max(0.0, 1.0 - h2h_home - random.uniform(0.1, 0.4)), 2)
        h2h_away = round(max(0.0, 1.0 - h2h_home - h2h_draw), 2)
        total_expected = home_goals_avg + away_goals_avg
        label_ou = 1 if total_expected >= 2.5 else 0
        if home_form > away_form + 1.5:
            label_1x2 = 0
        elif away_form > home_form + 1.5:
            label_1x2 = 2
        else:
            label_1x2 = random.choice([0, 1, 2])
        records.append(
            TrainRecord(
                match_id=f"SYN-{i+1}",
                features=[
                    home_goals_avg,
                    away_goals_avg,
                    round(random.uniform(0.5, 1.6), 2),
                    round(random.uniform(0.5, 1.6), 2),
                    home_form,
                    away_form,
                    h2h_home,
                    h2h_draw,
                    h2h_away,
                    home_goals_avg,
                    away_goals_avg,
                    float(random.choice([0, 1])),
                    random.randint(3, 10),
                    random.randint(3, 10),
                    0.0,
                ],
                label_1x2=label_1x2,
                label_ou=label_ou,
            )
        )
    return records


def train_model(
    records: list[TrainRecord],
    model_path: Path | str = Path("~/.sportoto/models/match_model.joblib").expanduser(),
) -> MatchModel:
    if not records:
        raise ValueError("no training records provided")
    model = MatchModel()
    features = [record.features for record in records]
    labels_1x2 = [record.label_1x2 for record in records]
    labels_ou = [record.label_ou for record in records]
    model.fit(features, labels_1x2, labels_ou)
    model.save(model_path)
    return model


__all__ = ["TrainRecord", "load_records_from_store", "generate_synthetic_training_records", "train_model"]
