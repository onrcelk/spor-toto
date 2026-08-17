import pytest

from sportoto.features import MatchFeatures
from sportoto.model import MatchModel


def test_model_ou_uses_xg_score_posterior():
    model = MatchModel()
    features = [[1.0] * 14] * 21
    model.fit(features, [0, 1, 2] * 7, [1] * 15 + [0] * 6)
    match = MatchFeatures("M1", "A", "B", "L1", "2026-08-17", home_xg_avg=2.2, away_xg_avg=1.8)
    prediction = model.predict(match)
    assert prediction.pred_over_2_5 > 0.5
    assert prediction.pred_over_2_5 + prediction.pred_under_2_5 == pytest.approx(1.0)
