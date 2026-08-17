from sportoto.advanced_analytics import parse_statsbomb_events


def test_statsbomb_parser_sums_xg_and_retains_shot_map():
    result = parse_statsbomb_events([
        {"id": "1", "type": {"name": "Shot"}, "team": {"name": "A"}, "player": {"name": "Striker"},
         "location": [90, 40], "shot": {"statsbomb_xg": 0.42, "outcome": {"name": "Goal"}, "freeze_frame": [{"location": [100, 40]}]}},
        {"id": "2", "type": {"name": "Shot"}, "team": {"name": "B"}, "location": [80, 30],
         "shot": {"statsbomb_xg": 0.10, "outcome": {"name": "Saved"}}},
    ])
    assert result.xg_by_team == {"A": 0.42, "B": 0.10}
    assert result.shots[0].x == 90
    assert result.shots[0].y == 40
    assert result.shots[0].freeze_frame_count == 1


def test_statsbomb_parser_counts_explicit_key_pass_and_defensive_events():
    result = parse_statsbomb_events([
        {"type": {"name": "Pass"}, "team": {"name": "A"}, "pass": {"shot_assist": True}},
        {"type": {"name": "Pressure"}, "team": {"name": "A"}},
        {"type": {"name": "Tackle"}, "team": {"name": "B"}},
    ])
    assert result.key_passes_by_team == {"A": 1}
    assert result.defensive_actions_by_team == {"A": 1, "B": 1}
    assert result.xa_by_team == {}
    assert result.ppda_by_team == {}
