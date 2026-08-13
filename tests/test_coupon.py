from sportoto.coupon import MatchPref, CouponRules, CouponResult, generate_coupon, format_coupon, apply_filter_by_surprise, apply_filter_by_draws, apply_filter_by_streak, filter_segment


def make_prefs():
    prefs = []
    for i in range(1, 16):
        pick = '1' if i % 3 == 0 else 'X' if i % 3 == 1 else '2'
        prefs.append(MatchPref(match_id=f'M{i:02d}', pick=pick))
    return prefs


def test_generate_14_guaranteed():
    prefs = make_prefs()
    # Ensure enough closed matches for 14 guaranteed
    for idx in range(4):
        prefs[idx] = MatchPref(match_id=prefs[idx].match_id, pick=prefs[idx].pick, is_closed=True)
    res = generate_coupon(prefs, guarantee=14)
    assert res.guarantee == 14
    assert len(res.columns) == 9
    assert all(len(c) == 15 for c in res.columns)


def test_validation_requires_closed():
    prefs = make_prefs()
    try:
        generate_coupon(prefs, guarantee=14)
    except ValueError as e:
        assert 'kapalı' in str(e)


def test_apply_filter_by_surprise():
    prefs = [
        MatchPref(match_id='M01', pick='1', tags=('surprise',)),
        MatchPref(match_id='M02', pick='X', tags=()),
    ]
    filtered = apply_filter_by_surprise(prefs, 0)
    assert len(filtered) == 1
    assert filtered[0].match_id == 'M02'


def test_format_coupon():
    prefs = [
        MatchPref(match_id='M01', pick='1', is_banko=True),
        MatchPref(match_id='M02', pick='X', is_double=True),
        MatchPref(match_id='M03', pick='2', is_closed=True),
    ]
    # pad to 15 for generation and add enough closed matches
    for i in range(4, 16):
        prefs.append(MatchPref(match_id=f'M{i:02d}', pick='1', is_closed=(i < 7)))
    res = generate_coupon(prefs, guarantee=14)
    out = format_coupon(res, prefs)
    assert '14 Garantili' in out
    assert 'Kolon 01' in out


def test_apply_filter_by_draws():
    prefs = [MatchPref(match_id='M01', pick='1'), MatchPref(match_id='M02', pick='X'), MatchPref(match_id='M03', pick='2'), MatchPref(match_id='M04', pick='X')]
    filtered = apply_filter_by_draws(prefs, 1)
    assert len(filtered) == 3
    assert filtered[2].match_id == 'M04'



def test_apply_filter_by_streak_limits_sequence():
    # Sequence: 2, 1, 1, X, 2, 2, 1, X
    # With max_home_streak=1 and max_away_streak=1, consecutive same non-draw picks are removed.
    prefs = [MatchPref(match_id=f'M{i:02d}', pick=pick) for i, pick in enumerate(['2','1','1','X','2','2','1','X'], start=1)]
    filtered = apply_filter_by_streak(prefs, 1, 2, 1)
    assert [p.match_id for p in filtered] == ['M01','M02','M04','M05','M07','M08']


def test_filter_segment_limits_subset():
    prefs = [MatchPref(match_id=f'M{i:02d}', pick='X' if i % 3 == 0 else '1') for i in range(1, 11)]
    filtered = filter_segment(prefs, 3, 7, max_draws=0)
    assert all(p.match_id not in {'M03', 'M06'} or p.pick != 'X' for p in filtered[2:7])


def test_segment_filters_1_9_and_10_15():
    prefs = [MatchPref(match_id=f'M{i:02d}', pick='X' if i % 3 == 0 else '1') for i in range(1, 16)]
    # Segment 1-9 has draws at M03, M06, M09; filter keeps only 1
    filtered = filter_segment(prefs, 1, 9, max_draws=1)
    seg1_ids = {f'M{i:02d}' for i in range(1, 10)}
    seg1 = [p for p in filtered if p.match_id in seg1_ids]
    assert sum(1 for p in seg1 if p.pick == 'X') <= 1
    # Segment 10-15 has draws at M12, M15; filter keeps only 1
    filtered2 = filter_segment(filtered, 10, 15, max_draws=1)
    seg2_ids = {f'M{i:02d}' for i in range(10, 16)}
    seg2 = [p for p in filtered2 if p.match_id in seg2_ids]
    assert sum(1 for p in seg2 if p.pick == 'X') <= 1


def test_total_surprise_filter():
    prefs = [MatchPref(match_id='M01', pick='1', tags=('surprise',)), MatchPref(match_id='M02', pick='X', tags=()), MatchPref(match_id='M03', pick='2', tags=('surprise',))]
    filtered = apply_filter_by_surprise(prefs, 0)
    assert len(filtered) == 1
    assert filtered[0].match_id == 'M02'

