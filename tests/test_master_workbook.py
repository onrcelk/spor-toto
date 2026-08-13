from sportoto.master_workbook import load_master_matches


def test_master_import_report():
    path = "/root/.hermes/cache/documents/doc_b78bce7de4d3_SportToto Master.xlsx"
    matches, report = load_master_matches(path)
    assert len(matches) == 4996
    assert report.periods == 335
    assert report.skipped_rows == 220
    assert {m.home_goals > m.away_goals for m in matches}
