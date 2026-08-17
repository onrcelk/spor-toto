"""Tests for the results audit module (hit/miss + O/U recording)."""
from __future__ import annotations

from sportoto.audit import (
    _match_real,
    _result_from_score,
    _ou_from_score,
    _load_dotenv_local,
)


def test_result_from_score():
    assert _result_from_score(2, 1) == "1"
    assert _result_from_score(0, 3) == "2"
    assert _result_from_score(1, 1) == "X"
    assert _result_from_score(None, 1) is None


def test_ou_from_score():
    assert _ou_from_score(2, 1) == "over"   # 3 > 2.5
    assert _ou_from_score(0, 0) == "under"  # 0 < 2.5
    assert _ou_from_score(1, 1) == "under"  # 2 < 2.5
    assert _ou_from_score(None, 2) is None


def test_match_real_exact_and_reversed():
    rows = [
        {"home_team": "Galatasaray A.Ş.", "away_team": "Fenerbahçe A.Ş.",
         "home_goals": 2, "away_goals": 1, "source": "test"},
    ]
    m = _match_real(rows, "Galatasaray A.Ş.", "Fenerbahçe A.Ş.")
    assert m is not None and m["home_goals"] == 2
    # reversed order
    m2 = _match_real(rows, "Fenerbahçe A.Ş.", "Galatasaray A.Ş.")
    assert m2 is not None and m2["home_goals"] == 2


def test_match_real_normalizes_aliases():
    rows = [
        {"home_team": "GALATASARAY", "away_team": "FENERBAHCE",
         "home_goals": 1, "away_goals": 1, "source": "test"},
    ]
    m = _match_real(rows, "Galatasaray A.Ş.", "Fenerbahçe A.Ş.")
    assert m is not None and m["away_goals"] == 1


def test_load_dotenv_local_no_crash_without_file(tmp_path, monkeypatch):
    # should not raise even if .env absent; just a smoke test
    monkeypatch.chdir(tmp_path)
    _load_dotenv_local(tmp_path / ".env")  # exists? no -> returns silently
