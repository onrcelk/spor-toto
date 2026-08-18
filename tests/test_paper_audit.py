from sportoto.paper_audit import audit_frozen_journal, audit_h15_survival


def record(match_id="M04", primary="1", selection="1X"):
    return {
        "record_id": f"run:{match_id}:v1", "run_id": "run", "match_id": match_id,
        "fixture": {"home": "A", "away": "B"},
        "prediction": {"raw": {"1": .6, "X": .3, "2": .1}, "calibrated": {"1": .6, "X": .3, "2": .1}},
        "ensemble": {"1": .6, "X": .3, "2": .1},
        "decision": {"primary": primary, "selection": selection, "banko": False},
        "post_match": {"actual": None, "hit": None, "error_type": None, "audit_at": None},
    }


def test_collector_separates_decision_hit_and_coupon_coverage():
    audited = audit_frozen_journal(
        [record()], {"M04": {"actual": "X", "status": "final_verified", "source": "official"}},
        {"M04": ["1", "X"]}, audited_at="2026-08-20T00:00:00+00:00",
    )[0]
    assert audited["decision_hit"] is False
    assert audited["coupon_covered"] is True
    assert audited["post_match"]["actual"] == "X"
    assert audited["post_match"]["hit"] is True
    assert audited["post_match"]["error_type"] == "missed_draw"
    assert audited["decision"]["primary"] == "1"


def test_collector_does_not_audit_pending_as_miss():
    audited = audit_frozen_journal(
        [record()], {"M04": {"actual": None, "status": "live"}}, {"M04": ["1", "X"]}
    )[0]
    assert audited["decision_hit"] is None
    assert audited["coupon_covered"] is None
    assert audited["post_match"]["hit"] is None
    assert audited["post_match"]["error_type"] == "pending"


def test_h15_survival_distinguishes_unfiltered_and_filtered_coverage():
    all_scenarios = [{"M01": "1", "M02": "X"}, {"M01": "2", "M02": "X"}]
    filtered = [{"M01": "1", "M02": "X"}]
    result = audit_h15_survival(all_scenarios, filtered, {"M01": "2", "M02": "X"},
                                [{"filter": "filter_X", "before": 2, "after": 1}])
    assert result == {
        "actual_result": {"M01": "2", "M02": "X"},
        "actual_in_all_scenarios": True,
        "actual_in_filtered": False,
        "eliminated_by": "filter_X",
    }


def test_collector_rejects_unknown_result_status():
    try:
        audit_frozen_journal([record()], {"M04": {"actual": "X", "status": "bogus"}}, {"M04": ["1", "X"]})
    except ValueError as exc:
        assert "result status" in str(exc)
    else:
        raise AssertionError("unknown result status must be rejected")
