"""Tests for the added ELO-difference feature (15-feature schema)."""
from __future__ import annotations

from sportoto.features import MatchFeatures
from sportoto.model import MatchModel


def test_matchfeatures_has_elo_diff_field():
    mf = MatchFeatures(match_id="M1", home_team="A", away_team="B", league="L",
                       kickoff_iso="2026-08-17T00:00:00+00:00", elo_diff=42.0)
    assert mf.elo_diff == 42.0
    vec = mf.to_vector()
    assert len(vec) == 15
    assert vec[-1] == 42.0


def test_trained_model_accepts_15_features():
    model = MatchModel()
    feats = [[1.0] * 15] * 21
    model.fit(feats, [0, 1, 2] * 7, [1] * 15 + [0] * 6)
    mf = MatchFeatures(match_id="M1", home_team="A", away_team="B", league="L",
                       kickoff_iso="2026-08-17T00:00:00+00:00", elo_diff=-15.0)
    pred = model.predict(mf)
    assert 0.0 <= pred.pred_home_win <= 1.0
    assert pred.predicted_1x2 in {"1", "X", "2"}
