"""Tests for the odds adapter + market-vs-model EV logic (local fixture only,
no paid API key required)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sportoto.odds import load_local_odds, market_vs_model
from sportoto.market import remove_vig, compute_ev, closing_line_delta


FIXTURE = {
    "odds": [
        {
            "home_team": "Galatasaray", "away_team": "Fenerbahce",
            "bookmaker": "test", "source": "local",
            "opening_1x2": {"1": 2.10, "X": 3.40, "2": 3.50},
            "closing_1x2": {"1": 2.00, "X": 3.30, "2": 3.70},
            "opening_ou": {"over": 1.80, "under": 2.05},
            "closing_ou": {"over": 1.75, "under": 2.10},
        }
    ]
}


def test_remove_vig_sums_to_one():
    imp = remove_vig({"1": 2.0, "X": 3.0, "2": 4.0})
    assert sum(imp.values()) == 1.0


def test_compute_ev_positive_edge():
    # model 55% vs decimal 2.20 => EV = 0.55*2.20 - 1 = +0.21
    assert compute_ev(0.55, 2.20) == pytest.approx(0.21)


def test_closing_line_delta_sign():
    # closing_line_delta returns vig-removed probability difference (closing - opening).
    # If home price is shortened while X/2 widen, home implied prob falls.
    d = closing_line_delta({"1": 2.00, "X": 3.40, "2": 3.50}, {"1": 2.10, "X": 3.30, "2": 3.40})
    assert d["1"] < 0  # home price lengthened (worse) closing -> prob down


def test_market_vs_model_local_fixture(tmp_path):
    p = tmp_path / "odds.json"
    p.write_text(json.dumps(FIXTURE), encoding="utf-8")
    odds = load_local_odds(str(p))
    assert len(odds) == 1
    preds = [{
        "home_team": "Galatasaray", "away_team": "Fenerbahce",
        "predicted_1x2": "1", "pred_home_win": 0.55, "pred_draw": 0.25, "pred_away_win": 0.20,
    }]
    joined = market_vs_model(odds, preds)
    assert len(joined) == 1
    row = joined[0]
    assert row["odds"] == 2.00
    assert row["ev"] is not None
    # closing_line_delta present and equals vig-removed diff (closing - opening)
    assert "1" in row["closing_line_delta"]
    from sportoto.market import closing_line_delta
    expected = closing_line_delta({"1": 2.10, "X": 3.40, "2": 3.50}, {"1": 2.00, "X": 3.30, "2": 3.70})
    assert abs(row["closing_line_delta"]["1"] - expected["1"]) < 1e-9
