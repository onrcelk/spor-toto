import json
from pathlib import Path

from sportoto.research_runner import run


def test_research_runner_processes_15_matches_and_eight_odds(tmp_path):
    journal = tmp_path / "journal.jsonl"
    rows = []
    for i in range(1, 16):
        rows.append(json.dumps({"match_id": f"M{i:02d}", "risk": {"flags": [], "banko_allowed": True}, "source_reliability": {}}))
    journal.write_text("\n".join(rows) + "\n")
    odds = tmp_path / "odds.json"
    odds.write_text(json.dumps({"matches": [{"match_index": i, "odds": {"1": 2, "X": 3, "2": 4}} for i in range(1, 9)]}))
    result = run(str(journal), str(odds), str(tmp_path / "out.jsonl"))
    assert result["matches"] == 15
    assert result["odds_found"] == 8
    assert result["market_available"] == 8
    assert result["verified"] == 0
    assert result["research_required"] == 7
    assert len((tmp_path / "out.jsonl").read_text().splitlines()) == 15


def test_research_runner_adds_squad_evidence_without_changing_odds_counts(tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text("\n".join(json.dumps({"match_id": f"M{i:02d}", "risk": {"flags": [], "banko_allowed": True}, "source_reliability": {}}) for i in range(1, 16)) + "\n")
    odds = tmp_path / "odds.json"
    odds.write_text(json.dumps({"matches": [{"match_index": i, "odds": {"1": 2, "X": 3, "2": 4}} for i in range(1, 9)]}))
    squad = tmp_path / "squad.json"
    squad.write_text(json.dumps({"source": "official", "matches": [{"match_id": "M04", "claims": [{"type": "injury", "player": "Player X", "status": "unavailable", "freshness": "fresh", "verified": True, "source_score": .96}]}]}))
    result = run(str(journal), str(odds), str(tmp_path / "out.jsonl"), str(squad))
    assert result["matches"] == 15
    assert result["odds_found"] == 8
    assert result["squad_found"] == 1
    assert result["squad_evidence"] == 1


def test_research_runner_generic_news_category(tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text(json.dumps({"match_id": "M04", "risk": {"flags": [], "banko_allowed": True}, "source_reliability": {}}) + "\n")
    odds = tmp_path / "odds.json"
    odds.write_text(json.dumps({"matches": []}))
    news = tmp_path / "news.json"
    news.write_text(json.dumps({"source": "official_news", "matches": [{"match_id": "M04", "claims": [{"type": "rotation", "value": "rotation_possible", "freshness": "fresh", "verified": True}]}]}))
    result = run(str(journal), str(odds), str(tmp_path / "out.jsonl"), news_path=str(news))
    assert result["categories"] == ["odds", "news"]
    assert result["news_found"] == 1
    assert result["news_evidence"] == 1
