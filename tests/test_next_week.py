import json

import pandas as pd

from sportoto.next_week import _team_summary, build_next_week_report


def test_next_week_report_writes_json(tmp_path):
    matches = tmp_path / "matches.json"
    matches.write_text(json.dumps({"matches": [{"match_index": 1, "home_team": "Galatasaray", "away_team": "Fenerbahçe", "date_text": "14.08.2026", "time_text": "20:00"}]}, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "report.json"
    result = build_next_week_report(matches, "data/sportoto_master_training.parquet", output, last_n=5)
    assert result["match_count"] == 1
    assert output.exists()
    assert result["matches"][0]["home_form"]["sample_size"] >= 0


def test_team_summary_excludes_other_teams():
    frame = pd.DataFrame([
        {"kickoff_iso": pd.Timestamp("2026-01-01", tz="UTC"), "home_team": "A", "away_team": "B", "actual_1x2": 0},
        {"kickoff_iso": pd.Timestamp("2026-01-02", tz="UTC"), "home_team": "C", "away_team": "D", "actual_1x2": 0},
    ])
    summary = _team_summary(frame, "A", pd.Timestamp("2026-01-03", tz="UTC"), last_n=5)
    assert summary["sample_size"] == 1
    assert summary["recent_matches"][0]["opponent"] == "B"
