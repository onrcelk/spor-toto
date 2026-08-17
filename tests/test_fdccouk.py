"""Tests for football-data.co.uk free odds adapter (real network, no key)."""
from __future__ import annotations

import pytest

from sportoto.odds import fetch_fdccouk

pytestmark = pytest.mark.network


def test_fetch_fdccouk_turkey_returns_closing_odds():
    odds = fetch_fdccouk("2324", "T1", "B365")
    assert len(odds) > 100
    first = odds[0]
    assert first.closing_1x2 and len(first.closing_1x2) == 3
    # B365 columns present for 1X2
    assert set(first.closing_1x2.keys()) == {"1", "X", "2"}
    # O/U present
    assert first.closing_ou is not None
    assert "over" in first.closing_ou and "under" in first.closing_ou
