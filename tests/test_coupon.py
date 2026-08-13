from sportoto.coupon import MatchPref, CouponRules, CouponResult, generate_coupon, format_coupon, apply_filter_by_surprise


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
