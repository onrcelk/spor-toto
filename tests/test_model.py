import pytest

from sportoto.model import MatchModel, MatchPrediction


def test_fit_then_predict_returns_prediction():
    model = MatchModel()
    features = [[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.25, 0.25, 1.0, 1.0, 0.0, 5.0, 5.0, 0.0]] * 21
    labels_1x2 = [0, 1, 2] * 7
    labels_ou = [1] * 15 + [0] * 6
    model.fit(features, labels_1x2, labels_ou)
    from sportoto.features import MatchFeatures
    mf = MatchFeatures(match_id="M1", home_team="A", away_team="B", league="L1", kickoff_iso="2026-08-13T00:00:00+00:00")
    prediction = model.predict(mf)
    assert isinstance(prediction, MatchPrediction)
    assert prediction.pred_home_win + prediction.pred_draw + prediction.pred_away_win == pytest.approx(1.0)
