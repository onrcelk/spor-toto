import json

from sportoto.next_week import build_next_week_report


def test_next_week_report_writes_json(tmp_path):
    matches = tmp_path / "matches.json"
    matches.write_text(json.dumps({"matches": [{"match_index": 1, "home_team": "Galatasaray", "away_team": "Fenerbahçe", "date_text": "14.08.2026", "time_text": "20:00"}]}, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "report.json"
    result = build_next_week_report(matches, "data/sportoto_master_training.parquet", output, last_n=5)
    assert result["match_count"] == 1
    assert output.exists()
    assert result["matches"][0]["home_form"]["sample_size"] >= 0
