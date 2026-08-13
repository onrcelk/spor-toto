from sportoto.features import MatchFeatures


def test_to_vector_length():
    mf = MatchFeatures(match_id="M1", home_team="A", away_team="B", league="L1", kickoff_iso="2026-08-13T00:00:00+00:00")
    assert len(mf.to_vector()) == len(MatchFeatures.field_names())


def test_field_names_non_empty():
    assert len(MatchFeatures.field_names()) >= 1
