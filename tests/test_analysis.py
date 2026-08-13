from sportoto.analysis import MatchAnalysis, analyze_match, format_analysis


def test_analyze_match_returns_analysis():
    from sportoto.features import MatchFeatures
    from sportoto.model import MatchModel
    match = MatchFeatures(match_id="M1", home_team="A", away_team="B", league="L1", kickoff_iso="2026-08-13T00:00:00+00:00")
    records = [
        MatchFeatures(
            match_id=f"SYN-{i}",
            home_team="A",
            away_team="B",
            league="L1",
            kickoff_iso="2026-08-13T00:00:00+00:00",
            home_goals_avg=1.5,
            away_goals_avg=1.2,
            home_conceded_avg=1.0,
            away_conceded_avg=1.1,
            home_form_points=6,
            away_form_points=4,
            h2h_home_win_rate=0.5,
            h2h_draw_rate=0.25,
            h2h_away_win_rate=0.25,
            home_xg_avg=1.5,
            away_xg_avg=1.1,
            is_derby=False,
            rest_days_home=6,
            rest_days_away=6,
        )
        for i in range(30)
    ]
    labels_1x2 = [0, 1, 2] * 10
    labels_ou = [1] * 20 + [0] * 10
    model = MatchModel()
    model.fit([m.to_vector() for m in records], labels_1x2, labels_ou)
    analysis = analyze_match(match, model, notes=["Test note"])
    assert isinstance(analysis, MatchAnalysis)
    assert analysis.home_team == "A"
    assert analysis.away_team == "B"
    assert len(analysis.notes) == 1


def test_format_analysis_includes_teams_and_prediction():
    from sportoto.features import MatchFeatures
    from sportoto.model import MatchModel
    match = MatchFeatures(match_id="M1", home_team="A", away_team="B", league="L1", kickoff_iso="2026-08-13T00:00:00+00:00")
    records = [
        MatchFeatures(
            match_id=f"SYN-{i}",
            home_team="A",
            away_team="B",
            league="L1",
            kickoff_iso="2026-08-13T00:00:00+00:00",
            home_goals_avg=1.5,
            away_goals_avg=1.2,
            home_conceded_avg=1.0,
            away_conceded_avg=1.1,
            home_form_points=6,
            away_form_points=4,
            h2h_home_win_rate=0.5,
            h2h_draw_rate=0.25,
            h2h_away_win_rate=0.25,
            home_xg_avg=1.5,
            away_xg_avg=1.1,
            is_derby=False,
            rest_days_home=6,
            rest_days_away=6,
        )
        for i in range(30)
    ]
    labels_1x2 = [0, 1, 2] * 10
    labels_ou = [1] * 20 + [0] * 10
    model = MatchModel()
    model.fit([m.to_vector() for m in records], labels_1x2, labels_ou)
    analysis = analyze_match(match, model)
    text = format_analysis(analysis)
    assert "A - B" in text
    assert "Over 2.5:" in text
