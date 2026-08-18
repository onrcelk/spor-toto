from sportoto.paper_pipeline import collect_and_persist_audit
from sportoto.paper_evaluation import evaluate_paper_runs


def record(match_id, primary="1", selection="1", coverage="confirmed", banko=True):
    return {
        "record_id": f"run:{match_id}:v1", "run_id": "run", "match_id": match_id,
        "prediction": {"raw": {"1": .6, "X": .3, "2": .1}, "calibrated": {"1": .6, "X": .3, "2": .1}},
        "ensemble": {"1": .6, "X": .3, "2": .1},
        "decision": {"primary": primary, "selection": selection, "banko": banko},
        "research": {"evidence_coverage": {"coverage": coverage}},
        "post_match": {"actual": None, "hit": None},
    }


def test_batch_collector_persists_idempotent_audit(tmp_path):
    records = [record("M01"), record("M02", primary="2", selection="X2", banko=False)]
    results = {
        "M01": {"actual": "1", "status": "final_verified", "source": "official"},
        "M02": {"actual": "X", "status": "final_verified", "source": "official"},
    }
    path = tmp_path / "audits" / "run.jsonl"
    audited = collect_and_persist_audit(records, results, {"M01": ["1"], "M02": ["X", "2"]}, path)
    assert len(audited) == 2
    assert len(path.read_text().splitlines()) == 2
    assert collect_and_persist_audit(records, results, {"M01": ["1"], "M02": ["X", "2"]}, path) == audited


def test_evaluation_excludes_pending_from_denominators():
    records = [
        {**record("M01"), "decision_hit": True, "coupon_covered": True,
         "post_match": {"actual": "1", "result_status": "final_verified"}},
        {**record("M02", coverage="none"), "decision_hit": None, "coupon_covered": None,
         "post_match": {"actual": None, "result_status": "live"}},
    ]
    report = evaluate_paper_runs(records)
    assert report["matches_total"] == 2
    assert report["final_results"] == 1
    assert report["decision_hit"]["count"] == 1
    assert report["decision_hit"]["accuracy"] == 1.0
    assert report["evidence_coverage"] == {"none": 1, "partial": 0, "confirmed": 1}
    h15 = {"actual_in_all_scenarios": True, "actual_in_filtered": False, "eliminated_by": "filter_X"}
    assert evaluate_paper_runs(records, h15)["h15"] == {
        "all_scenario_coverage": True, "filtered_coverage": False, "filter_elimination": "filter_X"
    }


def test_evaluation_reports_calibration_metrics_for_final_rows():
    row = record("M01")
    row["post_match"] = {"actual": "1", "result_status": "final_verified"}
    row["decision_hit"] = True
    row["coupon_covered"] = True
    report = evaluate_paper_runs([row])
    assert report["calibration"]["raw"]["sample_size"] == 1
    assert report["calibration"]["raw"]["brier"] >= 0
    assert report["calibration"]["raw"]["log_loss"] >= 0
