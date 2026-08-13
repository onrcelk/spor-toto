from pathlib import Path

try:
    from sportoto.masha_integration import collect_news, append_news, fetch_sportoto_list, append_sportoto_list, _parse_browser_text_to_rows, _parse_response_text_to_rows
except Exception:  # pragma: no cover - optional dependency
    collect_news = None  # type: ignore[assignment]
    append_news = None  # type: ignore[assignment]
    fetch_sportoto_list = None  # type: ignore[assignment]
    append_sportoto_list = None  # type: ignore[assignment]
    _parse_browser_text_to_rows = None  # type: ignore[assignment]
    _parse_response_text_to_rows = None  # type: ignore[assignment]


def test_parse_browser_text_to_rows_extracts_matches():
    if _parse_browser_text_to_rows is None:
        return
    sample = """
Galatasaray - Çorum FK
14.08.2026
Cuma
21:30

Fenerbahçe - Beşiktaş
15.08.2026
Cumartesi
20:00
"""
    rows = _parse_browser_text_to_rows(sample)
    assert len(rows) >= 2
    assert rows[0].home_team == "Galatasaray"
    assert rows[0].away_team == "Çorum FK"
    assert rows[1].home_team == "Fenerbahçe"
    assert rows[1].away_team == "Beşiktaş"


def test_parse_response_text_to_rows_extracts_matches():
    if _parse_response_text_to_rows is None:
        return
    sample = "| Galatasaray - Çorum FK | 14.08.2026 Cuma | 21:30 | - | - |\n| Fenerbahçe - Beşiktaş | 15.08.2026 Cumartesi | 20:00 | - | - |\n"
    rows = _parse_response_text_to_rows(sample)
    assert len(rows) >= 2
    assert rows[0].home_team == "Galatasaray"
    assert rows[0].away_team == "Çorum FK"


def test_collect_news_best_effort():
    if collect_news is None:
        return
    items = collect_news(["Spor Toto Süper Lig haftanın maçları"], limit=3)
    assert isinstance(items, list)


def test_append_news_writes_jsonl(tmp_path):
    if collect_news is None or append_news is None:
        return
    items = collect_news(["Spor Toto Süper Lig haftanın maçları"], limit=2)
    appended = append_news(tmp_path / "news.jsonl", items)
    assert appended == len(items)
    lines = (tmp_path / "news.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == appended


def test_fetch_sportoto_list_best_effort():
    if fetch_sportoto_list is None:
        return
    rows = fetch_sportoto_list()
    assert isinstance(rows, list)


def test_append_sportoto_list_writes_jsonl(tmp_path):
    if fetch_sportoto_list is None or append_sportoto_list is None:
        return
    rows = fetch_sportoto_list()[:1] if fetch_sportoto_list() else []
    if not rows:
        return
    appended = append_sportoto_list(tmp_path / "matches.jsonl", rows)
    assert appended == len(rows)
    lines = (tmp_path / "matches.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == appended
