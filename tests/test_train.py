from pathlib import Path

from sportoto.train import TrainRecord, generate_synthetic_training_records, load_records_from_store, train_model
from sportoto.store import PredictionStore


def test_generate_synthetic_training_records_returns_list():
    records = generate_synthetic_training_records(20)
    assert len(records) == 20
    assert all(isinstance(record, TrainRecord) for record in records)


def test_train_model_saves_model(tmp_path):
    records = generate_synthetic_training_records(30)
    model_path = tmp_path / "match_model.joblib"
    model = train_model(records, model_path)
    assert model_path.exists()
    assert model_path.stat().st_size > 0


def test_train_model_predict_after_training(tmp_path):
    records = generate_synthetic_training_records(40)
    model_path = tmp_path / "match_model.joblib"
    model = train_model(records, model_path)
    from sportoto.features import MatchFeatures
    mf = MatchFeatures(match_id="M1", home_team="A", away_team="B", league="L1", kickoff_iso="2026-08-13T00:00:00+00:00")
    prediction = model.predict(mf)
    assert prediction.pred_home_win >= 0.0
    assert prediction.pred_home_win <= 1.0
