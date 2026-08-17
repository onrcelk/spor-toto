"""Tests for the value-betting backtest module (real odds, network)."""
from __future__ import annotations

import pytest

from sportoto.value_backtest import run_value_backtest

pytestmark = pytest.mark.network


def test_value_backtest_runs_and_returns_metrics():
    res = run_value_backtest(season="2324", league="T1", bookmaker="B365", stake=1.0)
    assert res["odds_matched"] > 0
    assert res["bets_placed"] >= 0
    assert "roi_pct" in res
    assert "win_rate" in res
