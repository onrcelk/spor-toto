"""Tests for Super Lig data pipeline and hybrid prediction."""
from __future__ import annotations

from sportoto.superlig_data import build_frame
from sportoto.hybrid_predict import _is_superlig, SUPERLIG_TEAMS
from sportoto.identity import normalize_team_name


def test_superlig_frame_build(tmp_path):
    # tiny synthetic input
    import json
    data = [
        {"home_team": "Galatasaray", "away_team": "Fenerbahce", "kickoff_iso": "2023-01-01T00:00:00+00:00", "home_goals": 2, "away_goals": 1},
        {"home_team": "Fenerbahce", "away_team": "Besiktas", "kickoff_iso": "2023-01-08T00:00:00+00:00", "home_goals": 0, "away_goals": 0},
        {"home_team": "Besiktas", "away_team": "Galatasaray", "kickoff_iso": "2023-01-15T00:00:00+00:00", "home_goals": 1, "away_goals": 1},
    ]
    p = tmp_path / "sl.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out.parquet"
    df = build_frame(str(p), str(out))
    assert len(df) == 3
    assert "actual_1x2" in df.columns
    # first match: home(2)>away(1) => 0
    assert df.iloc[0]["actual_1x2"] == 0
    # third match: 1-1 => draw (1)
    assert df.iloc[2]["actual_1x2"] == 1
    assert out.exists()


def test_is_superlig_detects_tr_pairs():
    assert _is_superlig("Galatasaray A.Ş.", "Fenerbahçe A.Ş.") is True
    assert _is_superlig("B. Dortmund", "Bayern Münih") is False
    assert _is_superlig("Erzurumspor FK", "Galatasaray A.Ş.") is True
    assert _is_superlig("Arca Çorum FK", "Kasımpaşa") is True
    assert _is_superlig("Kocaelispor", "Amed Sportif Faaliyetler") is True


def test_superlig_teams_normalized_in_set():
    # her set elemani normalize_team_name ciktilariyla uyumlu olmali
    for t in SUPERLIG_TEAMS:
        assert normalize_team_name(t) == t, f"{t} not self-normalized"
