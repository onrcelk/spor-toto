from sportoto.tff_integration import fetch_fixtures, fetch_results, append_matches


def test_fetch_fixtures_returns_rows():
    rows = fetch_fixtures()
    assert isinstance(rows, list)
    if rows:
        row = rows[0]
        assert row.match_id and row.home_team and row.away_team
        assert row.league == "TFF"


def test_fetch_results_returns_rows():
    rows = fetch_results()
    assert isinstance(rows, list)
    if rows:
        row = rows[0]
        assert row.match_id
        assert row.result in {"1", "X", "2", None}
